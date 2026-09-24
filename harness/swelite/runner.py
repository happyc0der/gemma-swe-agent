"""Agent session driver: prompt construction, nudge loop, termination, patch extraction (README section 5)."""
from __future__ import annotations

import asyncio
import json
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.apps.app import EventsCompactionConfig
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from .compile import Compiler, ModelRegistry
from .graph import CodeGraph
from .sandbox import DockerSandbox
from .tasks import DataDir, Task
from .tools import Budget, HarnessLimits, SwegemmaContext

APP_NAME = "swegemma_eval"
USER_ID = "eval_user"
MAX_NUDGES = 3

NUDGE_TRUNCATED_TOOL_CALL = (
    "Your previous response reached the token limit before the tool call finished closing (<|tool_call|> was cut off). "
    "Do NOT repeat your prior reasoning in thought—emit your next tool call immediately, and if calling edit_file or write_file, "
    "split the change into smaller incremental edits."
)
NUDGE_MAX_TOKENS = (
    "Your previous response reached the token limit while thinking before a tool call was completed. "
    "Do NOT repeat your analysis in thought—keep reasoning under a few sentences and emit your next tool call immediately, "
    "or call submit_patch when you have completed and verified your changes."
)
NUDGE_CONTINUE = "Please continue your work using the available tools, or call submit_patch when you have completed and verified your changes."


def build_agent_prompt(task: Task, ctx: SwegemmaContext, graph_available: bool, listing: str) -> str:
    b = ctx.budget
    lim = ctx.limits
    parts = [
        f"You are evaluating a software engineering task for repository {task.repo}.\n\nProblem Statement:\n{task.problem_statement}\n",
    ]
    if task.hints_text.strip():
        parts.append(f"## Hints:\n{task.hints_text.strip()}\n")
    budget_lines = [f"- Time allowance: {b.time_minutes:.1f} minutes"]
    if b.tool_calls is not None:
        budget_lines.append(f"- Tool calls allowance: {b.tool_calls} calls")
    if b.turns is not None:
        budget_lines.append(f"- Max loop iterations: {b.turns} turns")
    parts.append("## Task Budget (Session terminates when any budget is exhausted)\n" + "\n".join(budget_lines) + "\n")
    parts.append(
        "## Execution Environment Rules\n"
        f"- Single command timeout: {lim.command_timeout_seconds} seconds (commands exceeding this fail without ending the session)\n"
        f"- Command output limit: {lim.max_stdout_chars} characters\n"
        f"- File view limit: {lim.max_file_lines} lines per read_file call\n"
        f"- File character limit: {lim.max_file_chars} characters per read_file call\n"
        "- Environment is offline (no network/PyPI access). All repository and test dependencies are ALREADY pre-installed. Do NOT attempt to run pip install or download packages.\n"
    )
    # Standard instructions 0-5. The README summarises rather than quotes these; wording here is our approximation.
    parts.append(
        "## Instructions\n"
        "0. All work must happen inside /workspace. Do not modify files outside it.\n"
        "1. Explore the repository to locate the code relevant to the problem statement and inspect existing conventions before editing.\n"
        "2. Implement a fix in the repository source code. Do not modify the test suite to make tests pass.\n"
        "3. Verify your change. Prefer targeted checks (for example `python3 -c \"...\"` assertions or a single targeted test) over full test sweeps.\n"
        "4. When the fix is complete and verified, call submit_patch. It captures `git diff HEAD` of /workspace.\n"
        "5. After submitting, return a brief final text summary of the change.\n"
    )
    if graph_available:
        parts.append(
            "## Code Intelligence Tools\n"
            "This repository has pre-built code graph and embedding data. Use these tools for fast, targeted navigation:\n"
            "- `search_similar_code(query)`: Find semantically similar functions/classes by keyword.\n"
            "- `get_code_neighbors(node)`: Find callers, callees, and definitions related to a symbol.\n"
            "- `get_code_subgraph(nodes)`: Get the induced subgraph for a set of symbols.\n"
        )
    parts.append("## Workspace Layout (first 150 entries of `find . -maxdepth 3`)\n```\n" + listing.strip() + "\n```\n")
    return "\n".join(parts)


class TurnBudgetPlugin(BasePlugin):
    """Counts LLM calls; short-circuits the model once the turn budget is exhausted."""

    def __init__(self, ctx: SwegemmaContext):
        super().__init__(name="swelite_turn_budget")
        self.ctx = ctx
        self.finish_reasons: list[str] = []
        self.last_text: str = ""
        self.usage: list[dict] = []

    async def before_model_callback(self, *, callback_context: CallbackContext, llm_request: LlmRequest) -> LlmResponse | None:
        self.ctx.llm_turns_used += 1
        if self.ctx.budget.turns is not None and self.ctx.llm_turns_used > self.ctx.budget.turns:
            return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="[budget] Max LLM turns exhausted.")]), turn_complete=True)
        if self.ctx.remaining_time <= 0:
            return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="[budget] Time exhausted.")]), turn_complete=True)
        return None

    async def after_model_callback(self, *, callback_context: CallbackContext, llm_response: LlmResponse) -> LlmResponse | None:
        fr = getattr(llm_response, "finish_reason", None)
        if fr is not None:
            self.finish_reasons.append(str(fr))
        if llm_response.content and llm_response.content.parts:
            texts = [p.text for p in llm_response.content.parts if getattr(p, "text", None)]
            if texts:
                self.last_text = "".join(texts)
        um = getattr(llm_response, "usage_metadata", None)
        if um is not None:
            self.usage.append({"prompt": getattr(um, "prompt_token_count", None), "candidates": getattr(um, "candidates_token_count", None), "total": getattr(um, "total_token_count", None)})
        return None


@dataclass
class TaskRunResult:
    instance_id: str
    agent_patch: str = ""
    patch_submitted: bool = False
    agent_error: str = ""
    tool_calls: int = 0
    llm_turns: int = 0
    elapsed_seconds: float = 0.0
    setup_seconds: float = 0.0
    nudges: int = 0
    events: list[dict] = field(default_factory=list)
    tool_log: list[dict] = field(default_factory=list)
    usage: list[dict] = field(default_factory=list)
    finish_reasons: list[str] = field(default_factory=list)


def _event_summary(ev: Any) -> dict:
    d: dict[str, Any] = {"author": getattr(ev, "author", None), "t": time.time()}
    content = getattr(ev, "content", None)
    if content and content.parts:
        parts = []
        for p in content.parts:
            if getattr(p, "function_call", None):
                fc = p.function_call
                parts.append({"function_call": {"name": fc.name, "args": dict(fc.args or {})}})
            elif getattr(p, "function_response", None):
                fr = p.function_response
                resp = fr.response
                s = json.dumps(resp, default=str)
                parts.append({"function_response": {"name": fr.name, "response": s[:4000]}})
            elif getattr(p, "text", None):
                parts.append({"text": p.text[:4000], "thought": bool(getattr(p, "thought", False))})
        d["parts"] = parts
    fr = getattr(ev, "finish_reason", None)
    if fr is not None:
        d["finish_reason"] = str(fr)
    return d


async def run_agent_sandbox(
    task: Task,
    data: DataDir,
    submission_dir: Path,
    registry: ModelRegistry,
    budget: Budget,
    limits: HarnessLimits,
    image: str = "swebench-sandbox:latest",
    log_path: Path | None = None,
    backend: str = "docker",
) -> TaskRunResult:
    result = TaskRunResult(instance_id=task.instance_id)
    t_setup = time.monotonic()
    from .verify import make_sandbox
    sandbox = make_sandbox(backend, image)
    log_fh = open(log_path, "w", encoding="utf-8") if log_path else None

    def log(msg: str) -> None:
        if log_fh:
            log_fh.write(msg + "\n")
            log_fh.flush()

    try:
        sandbox.start()
        sandbox.bootstrap(task, data)
        graph = CodeGraph(data.graph(task), data.embeddings(task))
        ctx = SwegemmaContext(sandbox=sandbox, graph=graph, budget=budget, limits=limits)
        compiler = Compiler(submission_dir, ctx.create_tools(), registry)
        root_agent = compiler.compile()
        plugin = TurnBudgetPlugin(ctx)
        app = App(
            name=APP_NAME,
            root_agent=root_agent,
            plugins=[plugin],
            events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=32768, event_retention_size=5),
            context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        )
        session_service = InMemorySessionService()
        runner = Runner(app=app, session_service=session_service)
        state = {"problem_description": task.problem_statement}
        if task.hints_text.strip():
            state["hints"] = task.hints_text.strip()
        session = await session_service.create_session(app_name=APP_NAME, user_id=USER_ID, state=state)
        listing = sandbox.workspace_listing()
        result.setup_seconds = time.monotonic() - t_setup

        ctx.start_agent_session()
        message = build_agent_prompt(task, ctx, graph.available, listing)
        log(f"=== USER ===\n{message}\n")
        consecutive_nudges = 0
        nudges_sent = 0
        while True:
            turn_has_tool_call = False
            last_text = ""
            last_finish = ""
            new_message = types.Content(role="user", parts=[types.Part(text=message)])
            try:
                async def _turn():
                    nonlocal turn_has_tool_call, last_text, last_finish
                    async for ev in runner.run_async(user_id=USER_ID, session_id=session.id, new_message=new_message):
                        s = _event_summary(ev)
                        result.events.append(s)
                        for p in s.get("parts", []):
                            if "function_call" in p:
                                turn_has_tool_call = True
                                log(f"--- CALL {p['function_call']['name']} {json.dumps(p['function_call']['args'])[:800]}")
                            elif "function_response" in p:
                                log(f"--- RESP {p['function_response']['name']} {p['function_response']['response'][:800]}")
                            elif "text" in p and not p.get("thought"):
                                last_text = p["text"]
                                log(f"--- TEXT ({s.get('author')}) {p['text'][:1500]}")
                        if s.get("finish_reason"):
                            last_finish = s["finish_reason"]
                remaining = max(1.0, ctx.remaining_time)
                await asyncio.wait_for(_turn(), timeout=remaining + 30)
            except asyncio.TimeoutError:
                result.agent_error = "session time budget exhausted mid-turn"
                break
            except Exception as e:  # model/proxy errors after retries
                result.agent_error = f"{type(e).__name__}: {e}"
                log("!!! " + traceback.format_exc())
                break

            if ctx.patch_submitted:
                break
            if ctx.remaining_time <= 0:
                result.agent_error = result.agent_error or "time budget exhausted"
                break
            if ctx.budget.turns is not None and ctx.llm_turns_used >= ctx.budget.turns:
                result.agent_error = result.agent_error or "turn budget exhausted"
                break
            if ctx.budget.tool_calls is not None and ctx.tool_calls_used >= ctx.budget.tool_calls and not turn_has_tool_call:
                result.agent_error = result.agent_error or "tool call budget exhausted"
                break
            consecutive_nudges = 0 if turn_has_tool_call else consecutive_nudges + 1
            if consecutive_nudges > MAX_NUDGES:
                result.agent_error = result.agent_error or "max nudges reached"
                break
            ltext = plugin.last_text or last_text
            if "<|tool_call" in ltext and "<|tool_call|>" not in ltext[ltext.rfind("<|tool_call"):]:
                message = NUDGE_TRUNCATED_TOOL_CALL
            elif any(k in (last_finish or "").upper() for k in ("MAX_TOKENS", "LENGTH")):
                message = NUDGE_MAX_TOKENS
            else:
                message = NUDGE_CONTINUE
            nudges_sent += 1
            log(f"=== NUDGE #{nudges_sent} ===\n{message}\n")

        result.nudges = nudges_sent
        result.patch_submitted = ctx.patch_submitted
        result.agent_patch = ctx.submitted_patch if ctx.patch_submitted else sandbox.extract_patch()
        result.tool_calls = ctx.tool_calls_used
        result.llm_turns = ctx.llm_turns_used
        result.elapsed_seconds = ctx.elapsed
        result.tool_log = ctx.tool_log
        result.usage = plugin.usage
        result.finish_reasons = plugin.finish_reasons
        try:
            await runner.close()
        except Exception:
            pass
    except Exception as e:
        result.agent_error = f"{type(e).__name__}: {e}"
        log("!!! " + traceback.format_exc())
        try:
            if sandbox.started:
                result.agent_patch = sandbox.extract_patch()
        except Exception:
            pass
    finally:
        sandbox.stop()
        if log_fh:
            log_fh.close()
    return result
