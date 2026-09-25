"""Subprocess sandbox backend (README 4.1) for hosts without a Docker daemon, e.g. Kaggle notebooks.

Creates an isolated temp dir with workspace/, tmp/, wheels/, sandbox/ and a private venv, rewrites
/workspace, /tmp, /wheels, /sandbox references in commands, and runs commands in a new process group
that is killed wholesale on timeout. Same interface as DockerSandbox.
"""
from __future__ import annotations

import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from .sandbox import ExecResult
from .tasks import DataDir, Task


class SubprocessSandbox:
    def __init__(self, python: str | None = None, base_dir: Path | None = None, name_prefix: str = "swelite"):
        self.python = python or sys.executable
        # Roots must NOT live under /tmp: exec() rewrites "/tmp" in commands to the sandbox's private tmp, which
        # would also rewrite the root path itself (seen on Linux where tempfile defaults to /tmp).
        base = Path(base_dir) if base_dir else Path(os.environ.get("SWELITE_SANDBOX_BASE", Path.home() / ".swelite_sandboxes"))
        base.mkdir(parents=True, exist_ok=True)
        self.root = Path(tempfile.mkdtemp(prefix=f"{name_prefix}_sandbox_", dir=str(base)))
        self.workspace = self.root / "workspace"
        self.tmp = self.root / "tmp"
        self.wheels = self.root / "wheels"
        self.sandbox_dir = self.root / "sandbox"
        self.venv = self.root / "venv"
        self.started = False
        self.name = self.root.name

    # ----- lifecycle -----
    def start(self) -> None:
        for d in (self.workspace, self.tmp, self.wheels, self.sandbox_dir):
            d.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([self.python, "-m", "venv", str(self.venv)], capture_output=True, text=True)
        if r.returncode != 0:  # e.g. Debian images without the venv module: fall back to virtualenv (pip-installable)
            subprocess.run([self.python, "-m", "pip", "install", "-q", "virtualenv"], capture_output=True, text=True)
            subprocess.run([self.python, "-m", "virtualenv", "-q", str(self.venv)], check=True, capture_output=True, text=True)
        self._pip("install", "-q", "--upgrade", "pip", "setuptools", "wheel")
        self.started = True

    def stop(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        self.started = False

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()

    # ----- helpers -----
    def _pip(self, *args: str, timeout: int = 900) -> subprocess.CompletedProcess:
        return subprocess.run([str(self.venv / "bin" / "python"), "-m", "pip", *args], capture_output=True, text=True, timeout=timeout)

    def _rewrite(self, command: str) -> str:
        return (command.replace("/workspace", str(self.workspace))
                .replace("/wheels", str(self.wheels))
                .replace("/sandbox", str(self.sandbox_dir))
                .replace("/tmp", str(self.tmp)))

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["PATH"] = f"{self.venv / 'bin'}{os.pathsep}{env.get('PATH', '')}"
        env["VIRTUAL_ENV"] = str(self.venv)
        env["TEST_TMPDIR"] = str(self.tmp)
        env["TMPDIR"] = str(self.tmp)
        env["HOME"] = str(self.root)
        env.pop("PYTHONPATH", None)
        return env

    def exec(self, command: str, timeout: float | None = 300, workdir: str = "/workspace") -> ExecResult:
        cmd = self._rewrite(command)
        cwd = self._rewrite(workdir)
        try:
            proc = subprocess.Popen(["/bin/bash", "-c", cmd], cwd=cwd, env=self._env(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace", start_new_session=True)
            out, err = proc.communicate(timeout=timeout)
            return ExecResult(proc.returncode, out, err, False)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:
                pass
            out, err = proc.communicate()
            return ExecResult(137, out or "", err or "", True)

    def copy_in(self, local: Path, remote: str) -> None:
        dst = Path(self._rewrite(remote))
        dst.parent.mkdir(parents=True, exist_ok=True)
        if Path(local).is_dir():
            shutil.copytree(local, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(local, dst)

    def write_text(self, remote: str, content: str) -> None:
        dst = Path(self._rewrite(remote))
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8")

    # ----- bootstrap -----
    def bootstrap(self, task: Task, data: DataDir, baseline_message: str = "baseline") -> None:
        snap = data.snapshot(task)
        if not snap.exists():
            raise FileNotFoundError(f"snapshot missing: {snap}")
        if not any(self.wheels.iterdir()):
            for w in data.wheels_dir.glob("*.whl"):
                shutil.copy2(w, self.wheels / w.name)
        for f in ("imp.py", "telnetlib.py"):
            src = data.docker_dir / f
            if src.exists():
                sp = subprocess.run([str(self.venv / "bin" / "python"), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"], capture_output=True, text=True).stdout.strip()
                if sp and not (Path(sp) / f).exists():
                    shutil.copy2(src, Path(sp) / f)
        self.copy_in(data.setup_py, "/sandbox/setup.py")
        for pkg in ("pytest", "pytest-timeout", "typer", "pdm-backend", "setuptools", "wheel", "poetry-core", "hatchling", "flit-core", "editables"):
            r = self._pip("install", "-q", "--no-index", f"--find-links={self.wheels}", pkg)
            if r.returncode != 0:
                self._pip("install", "-q", f"--find-links={self.wheels}", pkg)  # index fallback when online
        shutil.rmtree(self.workspace, ignore_errors=True)
        self.workspace.mkdir()
        import tarfile
        with tarfile.open(snap, "r:gz") as tf:
            try:
                tf.extractall(self.workspace, filter="fully_trusted")
            except TypeError:
                tf.extractall(self.workspace)
        self.exec("git config --global --add safe.directory '*'", timeout=30)
        r = self.exec(f"cd /workspace && python /sandbox/setup.py {shlex.quote(task.repo_short)}", timeout=900)
        if r.exit_code != 0:
            raise RuntimeError(f"setup.py failed: {r.stderr[-2000:]}")
        self.exec("cd /workspace && pip install -q --no-index --find-links=/wheels --no-build-isolation -e /workspace >/dev/null 2>&1 || true", timeout=900)
        r = self.exec(f"cd /workspace && git config user.email agent@eval && git config user.name Agent && git add -A && git commit -m {shlex.quote(baseline_message)} --allow-empty -q", timeout=120)
        if r.exit_code != 0:
            raise RuntimeError(f"baseline commit failed: {r.stderr[-2000:]}")

    def extract_patch(self) -> str:
        self.exec("cd /workspace && git add -N .", timeout=60)
        return self.exec("cd /workspace && git diff HEAD", timeout=120).stdout

    def workspace_listing(self, limit: int = 150) -> str:
        r = self.exec(f"cd /workspace && find . -maxdepth 3 -not -path './.git*' -not -path '*/__pycache__*' -not -name '*.pyc' | sort | head -n {limit}", timeout=60)
        return r.stdout
