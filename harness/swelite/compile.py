"""Declarative submission compiler: agent.yaml -> google-adk agent tree (README section 2)."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable

import yaml
from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool
from google.genai import types

MODEL_ALIASES = {
    "gemma-4-31b-it-qat-w4a16-ct", "gemma-4-31b-it", "gemma-4-31b", "gemma-4-27b-it", "gemma-4-27b",
    "gemma-4-26b-a4b-it", "gemma-4-26b-a4b", "diffusiongemma-26b-a4b-it", "gemma-4-12b-it", "gemma-4-12b",
    "gemma-4-9b-it", "gemma-4-9b", "gemma-4-e4b-it", "gemma-4-e4b", "gemma-4-e2b-it", "gemma-4-e2b",
}
FORBIDDEN_GEN_FIELDS = {"tools", "system_instruction", "http_options", "safety_settings", "response_schema"}
ALLOWED_GEN_FIELDS = {"temperature", "top_p", "top_k", "max_output_tokens", "presence_penalty", "frequency_penalty", "stop_sequences", "response_mime_type", "seed", "thinking_config"}
ROOT_NAMES = ("agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml")
MAX_INCLUDE_DEPTH = 10


class SubmissionError(ValueError):
    pass


def _safe_join(root: Path, base_dir: Path, rel: str) -> Path:
    if not rel or rel.startswith("/") or "\x00" in rel:
        raise SubmissionError(f"PathTraversalError: bad include path {rel!r}")
    # The organizers' sample uses `!include ../prompts/x.md` from sub_agents/, so `..` is fine
    # as long as the resolved path (symlinks included) stays inside the submission root.
    p = (base_dir / rel)
    resolved = p.resolve()
    if not str(resolved).startswith(str(root.resolve()) + os.sep):
        raise SubmissionError(f"PathTraversalError: {rel!r} resolves outside submission root")
    return p


def load_yaml(path: Path, root: Path, depth: int = 0, stack: tuple = ()) -> Any:
    if depth > MAX_INCLUDE_DEPTH:
        raise SubmissionError("include depth exceeded")
    if path.resolve() in stack:
        raise SubmissionError(f"include cycle at {path}")
    base_dir = path.parent

    class Loader(yaml.SafeLoader):
        pass

    def include(loader: yaml.SafeLoader, node: yaml.Node):
        rel = loader.construct_scalar(node)
        target = _safe_join(root, base_dir, rel)
        if target.suffix in (".md", ".txt"):
            return target.read_text(encoding="utf-8")
        if target.suffix in (".yaml", ".yml"):
            return load_yaml(target, root, depth + 1, stack + (path.resolve(),))
        raise SubmissionError(f"!include unsupported extension: {rel}")

    Loader.add_constructor("!include", include)
    with open(path, encoding="utf-8") as fh:
        return yaml.load(fh, Loader=Loader)


def find_root_config(sub_dir: Path) -> Path:
    found = [sub_dir / n for n in ROOT_NAMES if (sub_dir / n).exists()]
    if not found:
        raise SubmissionError("MissingRootConfigError: no agent.yaml in submission root")
    if len(found) > 1:
        raise SubmissionError(f"MultipleRootConfigsError: {[p.name for p in found]}")
    return found[0]


def normalize_model_name(m: str) -> str:
    for pre in ("openai/", "google/", "hosted_vllm/", "custom/"):
        if m.startswith(pre):
            m = m[len(pre):]
    return m


def discover_adapters(sub_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    ad = sub_dir / "adapters"
    if ad.is_dir():
        for d in sorted(ad.iterdir()):
            if d.is_dir() and (d / "adapter_config.json").exists() and (d / "adapter_model.safetensors").exists():
                out[d.name] = d
    return out


def collect_models(sub_dir: Path) -> set[str]:
    """All base models declared anywhere in the submission (single-model rule)."""
    models: set[str] = set()
    for p in list(sub_dir.rglob("*.yaml")) + list(sub_dir.rglob("*.yml")):
        if p.name == "eval_config.yaml":
            continue
        try:
            cfg = load_yaml(p, sub_dir)
        except Exception:
            continue
        if isinstance(cfg, dict) and isinstance(cfg.get("model"), str):
            models.add(normalize_model_name(cfg["model"]))
    return models


def build_generate_config(cfg: dict | None) -> types.GenerateContentConfig | None:
    if not cfg:
        return None
    bad = set(cfg) & FORBIDDEN_GEN_FIELDS
    if bad:
        raise SubmissionError(f"generate_content_config forbids {sorted(bad)}")
    unknown = set(cfg) - ALLOWED_GEN_FIELDS
    if unknown:
        raise SubmissionError(f"generate_content_config unknown fields {sorted(unknown)}")
    c = dict(cfg)
    if "max_output_tokens" in c and not (1 <= int(c["max_output_tokens"]) <= 32768):
        raise SubmissionError("max_output_tokens must be in 1..32768")
    if "thinking_config" in c and c["thinking_config"] is not None:
        tc = dict(c["thinking_config"])
        if isinstance(tc.get("thinking_level"), str):
            tc["thinking_level"] = tc["thinking_level"].upper()
        if "thinking_budget" in tc and not (1 <= int(tc["thinking_budget"]) <= 32768):
            raise SubmissionError("thinking_budget must be in 1..32768")
        if tc.get("thinking_level") == "NONE":
            # README: thinking_level "NONE" disables thinking; genai's enum has no NONE, so drop the config entirely.
            c.pop("thinking_config")
        else:
            c["thinking_config"] = types.ThinkingConfig(**tc)
    elif "thinking_config" in c:
        c.pop("thinking_config")
    return types.GenerateContentConfig(**c)


class ModelRegistry:
    """Maps model aliases (and adapters) to LiteLlm instances pointing at the local OpenAI-compatible server."""

    def __init__(self, api_base: str = "http://127.0.0.1:8000/v1", served_model: str | None = None, api_key: str = "EMPTY", num_retries: int = 5, extra_kwargs: dict | None = None):
        self.api_base = api_base
        self.served_model = served_model
        self.api_key = api_key
        self.num_retries = num_retries
        self.extra_kwargs = dict(extra_kwargs or {})  # forwarded to litellm.completion (proxy-only knobs, e.g. reasoning_effort)

    def get(self, alias: str, adapter: str | None) -> LiteLlm:
        alias = normalize_model_name(alias)
        if alias not in MODEL_ALIASES:
            raise SubmissionError(f"unknown model alias {alias!r}")
        served = adapter or self.served_model or alias
        return LiteLlm(model=f"openai/{served}", api_base=self.api_base, api_key=self.api_key, num_retries=self.num_retries, **self.extra_kwargs)


class Compiler:
    def __init__(self, sub_dir: Path, tools: dict[str, Callable], registry: ModelRegistry, skill_env: Any = None, script_timeout: int = 300):
        self.root = Path(sub_dir)
        self.tools = tools
        self.registry = registry
        self.skill_env = skill_env
        self.script_timeout = script_timeout
        self.adapters = discover_adapters(self.root)
        self.agent_count = 0
        self.models_seen: set[str] = set()

    def compile(self) -> Any:
        root_cfg_path = find_root_config(self.root)
        cfg = load_yaml(root_cfg_path, self.root)
        agent = self._build(cfg, root_cfg_path.parent, depth=0)
        if len(self.models_seen) > 1:
            raise SubmissionError(f"single-model rule violated: {sorted(self.models_seen)}")
        return agent

    def _build(self, cfg: dict, base_dir: Path, depth: int) -> Any:
        if depth > 50:
            raise SubmissionError("sub-agent depth exceeded")
        if not isinstance(cfg, dict):
            raise SubmissionError("agent config must be a mapping")
        self.agent_count += 1
        if self.agent_count > 500:
            raise SubmissionError("too many agents")
        cls = cfg.get("agent_class", "LlmAgent")
        name = cfg.get("name")
        if not name:
            raise SubmissionError("agent name is required")
        if cls in ("SequentialAgent", "ParallelAgent", "LoopAgent"):
            subs = [self._ref(s, base_dir, depth + 1) for s in cfg.get("sub_agents", [])]
            kw = {"name": name, "description": cfg.get("description", ""), "sub_agents": subs}
            if cls == "LoopAgent":
                mi = int(cfg.get("max_iterations", 500))
                if not (1 <= mi <= 500):
                    raise SubmissionError("max_iterations must be 1..500")
                return LoopAgent(max_iterations=mi, **kw)
            return (SequentialAgent if cls == "SequentialAgent" else ParallelAgent)(**kw)
        if cls != "LlmAgent":
            raise SubmissionError(f"unsupported agent_class {cls}")

        model_alias = cfg.get("model")
        if not model_alias:
            raise SubmissionError(f"agent {name}: model is required")
        self.models_seen.add(normalize_model_name(model_alias))
        adapter = cfg.get("adapter")
        if adapter is not None and adapter not in self.adapters:
            raise SubmissionError(f"agent {name}: adapter {adapter!r} not found under adapters/")
        model = self.registry.get(model_alias, adapter)

        tools = []
        for t in cfg.get("tools", []) or []:
            if isinstance(t, str):
                if t not in self.tools:
                    raise SubmissionError(f"agent {name}: unknown tool {t!r}")
                tools.append(FunctionTool(self.tools[t]))
            elif isinstance(t, dict) and "agent_tool" in t:
                at = t["agent_tool"]
                sub = self._ref(at, base_dir, depth + 1) if "config_path" in at else self._build(at, base_dir, depth + 1)
                tools.append(AgentTool(sub, skip_summarization=bool(at.get("skip_summarization", False))))
            elif isinstance(t, dict) and "name" in t:
                tools.append(self._build(t, base_dir, depth + 1))
            else:
                raise SubmissionError(f"agent {name}: bad tool entry {t!r}")

        subs = [self._ref(s, base_dir, depth + 1) for s in cfg.get("sub_agents", []) or []]
        instruction = cfg.get("instruction", "") or ""
        if len(instruction) > 1_000_000:
            raise SubmissionError("instruction too long")
        kw: dict[str, Any] = {
            "name": name, "model": model, "description": cfg.get("description", "") or "",
            "instruction": instruction, "tools": tools, "sub_agents": subs,
        }
        if cfg.get("global_instruction"):
            kw["global_instruction"] = cfg["global_instruction"]
        if cfg.get("output_key"):
            kw["output_key"] = cfg["output_key"]
        if cfg.get("include_contents") in ("default", "none"):
            kw["include_contents"] = cfg["include_contents"]
        for k in ("disallow_transfer_to_parent", "disallow_transfer_to_peers"):
            if cfg.get(k) is not None:
                kw[k] = bool(cfg[k])
        gcc = build_generate_config(cfg.get("generate_content_config"))
        if gcc is not None:
            kw["generate_content_config"] = gcc
        if cfg.get("skills"):
            dirs = []
            for rel in cfg["skills"]:
                d = _safe_join(self.root, base_dir, rel)
                if not (d / "SKILL.md").exists():
                    raise SubmissionError(f"agent {name}: skill {rel!r} has no SKILL.md")
                if sum(f.stat().st_size for f in d.rglob("*") if f.is_file()) > 50 * 1024 * 1024:
                    raise SubmissionError(f"agent {name}: skill {rel!r} exceeds 50 MiB")
                dirs.append(d)
            if self.skill_env is None:
                from .skills import load_skill_from_dir
                for d in dirs:
                    load_skill_from_dir(d)  # validation only (no sandbox in validate mode)
            else:
                from .skills import build_skill_toolset
                kw["tools"] = list(tools) + [build_skill_toolset(dirs, self.skill_env, self.script_timeout)]
        return LlmAgent(**kw)

    def _ref(self, ref: Any, base_dir: Path, depth: int) -> Any:
        if isinstance(ref, dict) and "config_path" in ref:
            p = _safe_join(self.root, base_dir, ref["config_path"])
            cfg = load_yaml(p, self.root)
            return self._build(cfg, p.parent, depth)
        if isinstance(ref, dict):
            return self._build(ref, base_dir, depth)
        raise SubmissionError(f"bad sub-agent reference {ref!r}")


def load_eval_config(sub_dir: Path) -> dict:
    p = Path(sub_dir) / "eval_config.yaml"
    if not p.exists():
        return {}
    cfg = load_yaml(p, Path(sub_dir)) or {}
    return cfg.get("evaluation", cfg) or {}


def validate_directory(sub_dir: Path) -> list[str]:
    """Cheap structural checks (extensions, symlinks, size)."""
    problems: list[str] = []
    allowed = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
    total = 0
    for p in Path(sub_dir).rglob("*"):
        if p.is_symlink():
            problems.append(f"symlink not allowed: {p}")
        if p.is_file():
            total += p.stat().st_size
            if p.suffix not in allowed:
                problems.append(f"disallowed extension: {p}")
    if total >= 3 * 1024**3:
        problems.append(f"unpacked size {total} >= 3 GiB")
    try:
        find_root_config(Path(sub_dir))
    except SubmissionError as e:
        problems.append(str(e))
    return problems
