"""Phase 2 verification in a fresh Container B (README section 8.2)."""
from __future__ import annotations

import shlex
from dataclasses import dataclass

from .sandbox import WORKSPACE, DockerSandbox
from .tasks import DataDir, Task, test_files_from_patch

PYTEST_CMD = (
    "cd /workspace && PYTHONSAFEPATH=1 python3 -m pytest {targets} "
    "-p no:anyio -o timeout=0 -o norecursedirs=\".* build dist venv\" -o python_classes=\"Test* *Test\" -q"
)


@dataclass
class VerifyResult:
    instance_id: str
    resolved: bool
    exit_code: int
    output: str
    error: str = ""
    apply_pass: int = 0


def apply_patch_in_container(sb: DockerSandbox, patch: str, remote: str = "/tmp/agent.patch") -> tuple[bool, int, str]:
    """4-pass resilient apply. Returns (ok, pass_number, last_error)."""
    sb.write_text(remote, patch if patch.endswith("\n") else patch + "\n")
    q = shlex.quote(remote)
    passes = [
        f"cd {WORKSPACE} && git apply --unsafe-paths -p1 {q}",
        f"cd {WORKSPACE} && git apply --unsafe-paths -3 {q}",
        f"cd {WORKSPACE} && git apply --unsafe-paths --ignore-space-change --ignore-whitespace {q}",
        f"cd {WORKSPACE} && git apply --unsafe-paths --recount {q}",
        f"cd {WORKSPACE} && git apply --unsafe-paths -p0 {q}",
        f"cd {WORKSPACE} && patch -p1 --batch --forward -l --dry-run < {q} && patch -p1 --batch --forward -l < {q}",
        f"cd {WORKSPACE} && patch -p0 --batch --forward -l --dry-run < {q} && patch -p0 --batch --forward -l < {q}",
    ]
    last = ""
    for i, cmd in enumerate(passes, 1):
        r = sb.exec(cmd, timeout=120)
        if r.exit_code == 0:
            return True, i, ""
        last = (r.stderr or r.stdout)[-1500:]
        # a partially-applied -3 could leave conflict markers; reset before the next pass
        sb.exec(f"cd {WORKSPACE} && git checkout -- . && git clean -fd -q", timeout=60)
    return False, 0, last


def verify_task(task: Task, data: DataDir, agent_patch: str, image: str = "swebench-sandbox:latest", timeout: int = 1800) -> VerifyResult:
    targets = test_files_from_patch(task.test_patch)
    with DockerSandbox(image=image, name_prefix="swelite-verify") as sb:
        try:
            sb.bootstrap(task, data, baseline_message="eval_baseline")
        except Exception as e:
            return VerifyResult(task.instance_id, False, -1, "", f"bootstrap failed: {e}")
        apply_pass = 0
        if agent_patch.strip():
            ok, apply_pass, err = apply_patch_in_container(sb, agent_patch)
            if not ok:
                return VerifyResult(task.instance_id, False, -1, "", f"Failed to apply agent_patch: {err}")
        # anti-tampering reset of target test files
        if targets:
            tq = " ".join(shlex.quote(t) for t in targets)
            sb.exec(f"cd {WORKSPACE} && git checkout HEAD -- {tq} 2>/dev/null || true", timeout=60)
            sb.exec(f"cd {WORKSPACE} && git clean -f -- {tq} 2>/dev/null || true", timeout=60)
        ok, _, err = apply_patch_in_container(sb, task.test_patch, remote="/tmp/test.patch")
        if not ok:
            return VerifyResult(task.instance_id, False, -1, "", f"Failed to apply test_patch: {err}")
        sb.exec(f"cd {WORKSPACE} && python3 /sandbox/setup.py --fast-path {shlex.quote(task.repo_short)}", timeout=300)
        cmd = PYTEST_CMD.format(targets=" ".join(shlex.quote(t) for t in targets))
        r = sb.exec(cmd, timeout=timeout)
        out = (r.stdout + "\n" + r.stderr)[-20000:]
        return VerifyResult(task.instance_id, r.exit_code == 0, r.exit_code, out, "" if not r.timed_out else "pytest timed out", apply_pass)
