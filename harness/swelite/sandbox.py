"""Docker sandbox lifecycle mirroring swegemma's ContainerManager (README section 4)."""
from __future__ import annotations

import shlex
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path

from .tasks import DataDir, Task

WORKSPACE = "/workspace"


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
    ):
        self.image = image
        self.memory = memory
        self.cpus = cpus
        self.network = network
        self.name = f"{name_prefix}-{uuid.uuid4().hex[:10]}"
        self.started = False

    # ----- lifecycle -----
    def start(self) -> None:
        cmd = [
            "docker", "run", "-d", "--name", self.name,
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
            "find /workspace -type l -xtype l -delete 2>/dev/null || true",
            timeout=300,
        )
        if r.exit_code != 0:
            raise RuntimeError(f"snapshot extraction failed: {r.stderr[-2000:]}")
        # setup.py: git exclude, editable install, wheel-resolved deps, pytest.ini, conftest.py
        r = self.exec(f"cd {WORKSPACE} && python3 /sandbox/setup.py {shlex.quote(task.repo_short)}", timeout=600)
        if r.exit_code != 0:
            raise RuntimeError(f"setup.py failed: {r.stderr[-2000:]}")
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


def build_image(data: DataDir, tag: str = "swebench-sandbox:latest", public: bool = True) -> None:
    """Build the sandbox image from the dataset's Dockerfile with wheels/ in the context."""
    import shutil
    import tempfile

    ctx = Path(tempfile.mkdtemp(prefix="swelite-build-"))
    try:
        for f in ("imp.py", "telnetlib.py"):
            shutil.copy(data.docker_dir / f, ctx / f)
        shutil.copytree(data.wheels_dir, ctx / "wheels")
        dockerfile = data.docker_dir / ("Dockerfile.public" if public else "Dockerfile.sandbox")
        shutil.copy(dockerfile, ctx / "Dockerfile")
        subprocess.run(["docker", "build", "-t", tag, str(ctx)], check=True)
    finally:
        shutil.rmtree(ctx, ignore_errors=True)
