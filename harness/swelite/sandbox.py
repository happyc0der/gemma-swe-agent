"""Docker sandbox lifecycle mirroring swegemma's ContainerManager (README section 4)."""
from __future__ import annotations

import platform
import shlex
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .tasks import DataDir, Task

WORKSPACE = "/workspace"
# The wheel cache is manylinux x86_64, so on Apple Silicon hosts the sandbox must run under amd64 emulation.
DEFAULT_PLATFORM = "linux/amd64" if platform.machine() in ("arm64", "aarch64") else None


@dataclass
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class DockerSandbox:
    """One container. Network none, 4 GiB RAM, 2 vCPUs, /workspace, /wheels baked into the image."""

    def __init__(
        self,
        image: str = "swebench-sandbox:latest",
        memory: str = "4g",
        cpus: float = 2.0,
        network: str = "none",
        name_prefix: str = "swelite",
        docker_platform: str | None = DEFAULT_PLATFORM,
    ):
        self.image = image
        self.docker_platform = docker_platform
        self.memory = memory
        self.cpus = cpus
        self.network = network
        self.name = f"{name_prefix}-{uuid.uuid4().hex[:10]}"
        self.started = False

    # ----- lifecycle -----
    def start(self) -> None:
        cmd = [
            "docker", "run", "-d", "--name", self.name,
            *(["--platform", self.docker_platform] if self.docker_platform else []),
            "--network", self.network,
            "--memory", self.memory, "--memory-swap", self.memory,
            f"--cpus={self.cpus}",
            "-e", "TEST_TMPDIR=/tmp",
            "-w", WORKSPACE,
            self.image, "sleep", "infinity",
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        self.started = True

    def stop(self) -> None:
        if self.started:
            subprocess.run(["docker", "rm", "-f", self.name], capture_output=True, text=True)
            self.started = False

    def __enter__(self) -> "DockerSandbox":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # ----- primitives -----
    def exec(self, command: str, timeout: float | None = 300, workdir: str = WORKSPACE) -> ExecResult:
        """Run `command` via /bin/bash -c inside the container.

        Uses coreutils `timeout -s KILL` in-container so the process group dies on timeout,
        with a subprocess-level timeout as a backstop.
        """
        if timeout is not None:
            inner = f"timeout -s KILL {int(max(1, timeout))} /bin/bash -c {shlex.quote(command)}"
        else:
            inner = f"/bin/bash -c {shlex.quote(command)}"
        cmd = ["docker", "exec", "-w", workdir, self.name, "/bin/bash", "-c", inner]
        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, errors="replace",
                timeout=(timeout + 15) if timeout is not None else None,
            )
        except subprocess.TimeoutExpired as e:
            return ExecResult(137, (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""),
                              (e.stderr or b"").decode(errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or ""), True)
        timed_out = res.returncode == 137 and timeout is not None
        return ExecResult(res.returncode, res.stdout, res.stderr, timed_out)

    def copy_in(self, local: Path, remote: str) -> None:
        subprocess.run(["docker", "cp", str(local), f"{self.name}:{remote}"], check=True, capture_output=True)

    def write_text(self, remote: str, content: str) -> None:
        cmd = ["docker", "exec", "-i", self.name, "/bin/bash", "-c", f"mkdir -p $(dirname {shlex.quote(remote)}) && cat > {shlex.quote(remote)}"]
        subprocess.run(cmd, input=content, text=True, check=True, capture_output=True)

    # ----- bootstrap (README 4.2 steps 1-7) -----
    def bootstrap(self, task: Task, data: DataDir, baseline_message: str = "baseline") -> None:
        snap = data.snapshot(task)
        if not snap.exists():
            raise FileNotFoundError(f"snapshot missing: {snap}")
        self.exec(f"rm -rf {WORKSPACE} && mkdir -p {WORKSPACE} /sandbox", timeout=60)
        self.copy_in(snap, "/tmp/snapshot.tgz")
        self.copy_in(data.setup_py, "/sandbox/setup.py")
        # Extract; tolerate a single top-level directory inside the archive.
        r = self.exec(
            "set -e; mkdir -p /tmp/snap && tar -xzf /tmp/snapshot.tgz -C /tmp/snap; "
            "n=$(ls -A /tmp/snap | wc -l); "
            "if [ \"$n\" = 1 ] && [ -d \"/tmp/snap/$(ls -A /tmp/snap)\" ] && [ ! -d /tmp/snap/.git ]; then "
            "  src=\"/tmp/snap/$(ls -A /tmp/snap)\"; else src=/tmp/snap; fi; "
            f"cp -a \"$src\"/. {WORKSPACE}/; rm -rf /tmp/snap /tmp/snapshot.tgz; "
            "find /workspace -type l -xtype l -delete 2>/dev/null || true; "
            "chown -R root:root /workspace; git config --global --add safe.directory '*'",
            timeout=300,
        )
        if r.exit_code != 0:
            raise RuntimeError(f"snapshot extraction failed: {r.stderr[-2000:]}")
        # setup.py: git exclude, editable install, wheel-resolved deps, pytest.ini, conftest.py
        r = self.exec(f"cd {WORKSPACE} && python3 /sandbox/setup.py {shlex.quote(task.repo_short)}", timeout=600)
        if r.exit_code != 0:
            raise RuntimeError(f"setup.py failed: {r.stderr[-2000:]}")
        # The official harness streams a cached site-packages built from /wheels. Approximate it by letting pip
        # resolve the repo's own dependency pins (setup.py / pyproject) offline against /wheels, best effort.
        self.exec(
            f"cd {WORKSPACE} && pip install -q --no-index --find-links=/wheels --no-build-isolation -e {WORKSPACE} >/dev/null 2>&1 || true",
            timeout=600,
        )
        r = self.exec(
            f"cd {WORKSPACE} && git config user.email agent@eval && git config user.name Agent && "
            f"git add -A && git commit -m {shlex.quote(baseline_message)} --allow-empty -q",
            timeout=120,
        )
        if r.exit_code != 0:
            raise RuntimeError(f"baseline commit failed: {r.stderr[-2000:]}")

    def extract_patch(self) -> str:
        """`git add -N . && git diff HEAD` (README 8.1)."""
        self.exec(f"cd {WORKSPACE} && git add -N .", timeout=60)
        r = self.exec(f"cd {WORKSPACE} && git diff HEAD", timeout=120)
        return r.stdout

    def workspace_listing(self, limit: int = 150) -> str:
        r = self.exec(
            f"cd {WORKSPACE} && find . -maxdepth 3 -not -path './.git*' -not -path '*/__pycache__*' -not -name '*.pyc' | sort | head -n {limit}",
            timeout=60,
        )
        return r.stdout


LOCAL_EXTRA_DOCKERFILE = """
# swelite-local layer: test-only dependencies the public wheel cache lacks (the organizers' private image has them).
FROM swebench-sandbox:public
RUN pip install --no-cache-dir {pkgs}
"""

LOCAL_EXTRA_PKGS = [
    # fastapi tests
    "dirty-equals", "inline-snapshot", "sqlmodel", "flask", "anyio[trio]", "PyJWT", "pyyaml", "passlib[bcrypt]",
    "python-multipart", "email-validator", "jinja2", "orjson", "ujson", "pydantic-settings", "pydantic-extra-types", "httpx",
    # rich tests
    "attrs",
    # requests tests
    "pytest-httpbin", "httpbin", "trustme", "PySocks", "chardet",
]


def build_image(data: DataDir, tag: str = "swebench-sandbox:latest", public: bool = True, docker_platform: str | None = DEFAULT_PLATFORM, local_extras: bool = True) -> None:
    """Build the sandbox image from the dataset's Dockerfile with wheels/ in the context.

    With local_extras, adds a layer installing test-only deps from PyPI (needs internet at build time) so the
    public tasks' test suites can run locally; the resulting image is tagged `tag`, the pure one `swebench-sandbox:public`.
    """
    import shutil
    import tempfile

    ctx = Path(tempfile.mkdtemp(prefix="swelite-build-"))
    try:
        for f in ("imp.py", "telnetlib.py"):
            shutil.copy(data.docker_dir / f, ctx / f)
        shutil.copytree(data.wheels_dir, ctx / "wheels")
        dockerfile = data.docker_dir / ("Dockerfile.public" if public else "Dockerfile.sandbox")
        shutil.copy(dockerfile, ctx / "Dockerfile")
        plat = ["--platform", docker_platform] if docker_platform else []
        base_tag = "swebench-sandbox:public" if local_extras else tag
        import os
        env = {**os.environ, "DOCKER_BUILDKIT": "1"}  # needs the buildx plugin (brew install docker-buildx)
        subprocess.run(["docker", "build", *plat, "--pull", "-t", base_tag, str(ctx)], check=True, env=env)
        if local_extras:
            (ctx / "Dockerfile.local").write_text(LOCAL_EXTRA_DOCKERFILE.format(pkgs=" ".join(shlex.quote(p) for p in LOCAL_EXTRA_PKGS)))
            subprocess.run(["docker", "build", *plat, "-t", tag, "-f", str(ctx / "Dockerfile.local"), str(ctx)], check=True, env=env)
    finally:
        shutil.rmtree(ctx, ignore_errors=True)
