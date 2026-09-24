"""Task loading and dataset path resolution."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    instance_id: str
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str
    patch: str
    test_patch: str
    created_at: str = ""

    @property
    def repo_short(self) -> str:
        return self.repo.split("/")[-1]

    @property
    def commit_name(self) -> str:
        return f"{self.repo_short}_{self.base_commit}"


def load_tasks(path: Path, ids: list[str] | None = None) -> list[Task]:
    tasks: list[Task] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            t = Task(
                instance_id=d["instance_id"],
                repo=d["repo"],
                base_commit=d["base_commit"],
                problem_statement=d.get("problem_statement", ""),
                hints_text=d.get("hints_text", "") or "",
                patch=d.get("patch", "") or "",
                test_patch=d.get("test_patch", "") or "",
                created_at=d.get("created_at", "") or "",
            )
            if ids is None or t.instance_id in ids:
                tasks.append(t)
    return tasks


def test_files_from_patch(test_patch: str) -> list[str]:
    """Paths referenced by `+++ b/<path>` lines in a unified diff."""
    files: list[str] = []
    for m in re.finditer(r"^\+\+\+ b/(\S+)", test_patch, flags=re.M):
        p = m.group(1)
        if p not in files:
            files.append(p)
    return files


class DataDir:
    """Competition data layout: tasks.jsonl, snapshots/, graphs/, embeddings/, wheels/, docker/, sandbox/."""

    MIN_BYTES = 100  # files at or below this are treated as absent (Kaggle dropped hard-link twins)

    def __init__(self, root: Path):
        self.root = Path(root)

    @property
    def tasks_path(self) -> Path:
        return self.root / "tasks.jsonl"

    def snapshot(self, task: Task) -> Path:
        return self.root / "snapshots" / f"{task.instance_id}.tgz"

    def _pick(self, subdir: str, task: Task, ext: str) -> Path | None:
        for name in (task.instance_id, task.commit_name):
            p = self.root / subdir / f"{name}{ext}"
            if p.exists() and p.stat().st_size > self.MIN_BYTES:
                return p
        return None

    def graph(self, task: Task) -> Path | None:
        return self._pick("graphs", task, ".json")

    def embeddings(self, task: Task) -> Path | None:
        return self._pick("embeddings", task, ".npz")

    @property
    def wheels_dir(self) -> Path:
        return self.root / "wheels"

    @property
    def setup_py(self) -> Path:
        return self.root / "sandbox" / "setup.py"

    @property
    def docker_dir(self) -> Path:
        return self.root / "docker"
