from pathlib import Path

import pytest

from swelite.compile import Compiler, ModelRegistry, SubmissionError
from tests.test_compile import dummy_tools


def _sub(tmp_path: Path, skill_name: str):
    d = tmp_path / "skills" / skill_name
    (d / "scripts").mkdir(parents=True)
    (d / "SKILL.md").write_text(f"---\nname: {skill_name}\ndescription: x\n---\nbody\n")
    (d / "scripts" / "s.py").write_text("print('hi')\n")
    (tmp_path / "agent.yaml").write_text(f"name: a\nmodel: gemma-4-31b-it\ninstruction: hi\ntools: [run_command]\nskills: [skills/{skill_name}]\n")


def test_skill_validates(tmp_path):
    _sub(tmp_path, "repo-tools")
    Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()


def test_skill_name_must_match_dir_and_be_kebab(tmp_path):
    _sub(tmp_path, "repo_tools")
    with pytest.raises(Exception):
        Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()


def test_skill_missing_manifest(tmp_path):
    (tmp_path / "skills" / "x").mkdir(parents=True)
    (tmp_path / "agent.yaml").write_text("name: a\nmodel: gemma-4-31b-it\ninstruction: hi\nskills: [skills/x]\n")
    with pytest.raises(SubmissionError):
        Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()
