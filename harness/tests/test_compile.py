from pathlib import Path

import pytest

from swelite.compile import Compiler, ModelRegistry, SubmissionError, load_eval_config, validate_directory

SAMPLE = Path(__file__).resolve().parents[2] / "data" / "competition" / "sample_submission"
NAMES = ["run_command", "submit_patch", "get_status", "read_file", "edit_file", "write_file", "get_code_neighbors", "search_similar_code", "get_code_subgraph"]


def dummy_tools():
    out = {}
    for n in NAMES:
        def f(**kw):
            return "{}"
        f.__name__ = n
        f.__doc__ = n
        out[n] = f
    return out


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample submission not downloaded")
def test_sample_compiles():
    assert validate_directory(SAMPLE) == []
    c = Compiler(SAMPLE, dummy_tools(), ModelRegistry())
    agent = c.compile()
    assert agent.name == "swe_baseline_agent"
    assert len(agent.tools) == 10  # 9 tools + agent_tool
    assert set(c.adapters) == {"main_lora", "tool_lora"}
    assert c.models_seen == {"gemma-4-31b-it-qat-w4a16-ct"}
    gcc = agent.generate_content_config
    assert gcc.temperature == 0.2 and gcc.max_output_tokens == 16384
    assert gcc.thinking_config.thinking_budget == 4096
    ec = load_eval_config(SAMPLE)
    assert ec["max_tool_calls"] == 10


def test_traversal_blocked(tmp_path):
    (tmp_path / "agent.yaml").write_text("name: a\nmodel: gemma-4-31b-it\ninstruction: !include ../secret.md\n")
    with pytest.raises(SubmissionError):
        Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()


def test_two_models_rejected(tmp_path):
    (tmp_path / "sub_agents").mkdir()
    (tmp_path / "sub_agents" / "b.yaml").write_text("name: b\nmodel: gemma-4-9b-it\ninstruction: hi\n")
    (tmp_path / "agent.yaml").write_text("name: a\nmodel: gemma-4-31b-it\ninstruction: hi\nsub_agents:\n  - config_path: sub_agents/b.yaml\n")
    with pytest.raises(SubmissionError):
        Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()


def test_forbidden_gen_field(tmp_path):
    (tmp_path / "agent.yaml").write_text("name: a\nmodel: gemma-4-31b-it\ninstruction: hi\ngenerate_content_config:\n  system_instruction: x\n")
    with pytest.raises(SubmissionError):
        Compiler(tmp_path, dummy_tools(), ModelRegistry()).compile()
