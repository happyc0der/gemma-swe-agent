"""ADK skills support: SKILL.md directories whose scripts run inside the task sandbox (README 'Skill Structure & Sandboxing')."""
from __future__ import annotations

import shlex
from pathlib import Path

from google.adk.environment._base_environment import BaseEnvironment, ExecutionResult
from google.adk.skills import load_skill_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from .tools import SwegemmaContext

SKILLS_FOLDER = "/opt/skills"  # outside /workspace so materialized scripts never enter the patch


class SandboxEnvironment(BaseEnvironment):
    """Runs skill scripts in the same sandbox as run_command, debiting the tool-call budget."""

    def __init__(self, ctx: SwegemmaContext):
        super().__init__()
        self.ctx = ctx
        self._initialized = True

    @property
    def working_dir(self) -> Path:
        return Path("/workspace")

    async def initialize(self) -> None:
        self._initialized = True

    async def close(self) -> None:
        pass

    async def execute(self, command: str, *, timeout: float | None = None) -> ExecutionResult:
        import json
        raw = self.ctx.run_command(command)  # gated + logged like any run_command call
        d = json.loads(raw)
        if d.get("status") == "ok":
            return ExecutionResult(exit_code=0, stdout=d.get("stdout", ""), stderr="")
        det = d.get("details", {})
        return ExecutionResult(exit_code=int(det.get("exit_code", 1) or 1), stdout=det.get("stdout", ""), stderr=det.get("stderr", d.get("error_message", "")), timed_out=d.get("error_type") == "TimeoutExceeded")

    async def read_file(self, path: Path) -> bytes:
        r = self.ctx.sandbox.exec(f"cat -- {shlex.quote(str(path))}", timeout=30)
        if r.exit_code != 0:
            raise FileNotFoundError(str(path))
        return r.stdout.encode("utf-8")

    async def write_file(self, path: Path, content: str | bytes) -> None:
        text = content.decode("utf-8") if isinstance(content, bytes) else content
        self.ctx.sandbox.write_text(str(path), text)


def build_skill_toolset(skill_dirs: list[Path], env: SandboxEnvironment, script_timeout: int = 300) -> SkillToolset:
    skills = [load_skill_from_dir(d) for d in skill_dirs]
    return SkillToolset(skills=skills, environment=env, skills_folder=SKILLS_FOLDER, script_timeout=script_timeout)
