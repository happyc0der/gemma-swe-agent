"""SwegemmaContext and the 9 sandboxed tools (README section 6)."""
from __future__ import annotations

import json
import shlex
import time
from dataclasses import dataclass, field
from typing import Callable

from .editing import apply_replacement
from .graph import CodeGraph
from .sandbox import WORKSPACE, DockerSandbox


@dataclass
class Budget:
    time_minutes: float = 60.0
    tool_calls: int | None = None
    turns: int | None = 500


@dataclass
class HarnessLimits:
    command_timeout_seconds: int = 300
    max_stdout_chars: int = 5000
    max_file_lines: int = 150
    max_file_chars: int = 10000


def _err(error_type: str, message: str, **details) -> dict:
    d = {"status": "error", "error_type": error_type, "error_message": message}
    if details:
        d["details"] = details
    return d


@dataclass
class SwegemmaContext:
    sandbox: DockerSandbox
    graph: CodeGraph
    budget: Budget = field(default_factory=Budget)
    limits: HarnessLimits = field(default_factory=HarnessLimits)
    tool_calls_used: int = 0
    llm_turns_used: int = 0
    patch_submitted: bool = False
    submitted_patch: str = ""
    agent_start_time: float | None = None
    tool_log: list[dict] = field(default_factory=list)

    # ----- timing -----
    def start_agent_session(self) -> None:
        self.agent_start_time = time.monotonic()

    @property
    def elapsed(self) -> float:
        return 0.0 if self.agent_start_time is None else time.monotonic() - self.agent_start_time

    @property
    def remaining_time(self) -> float:
        return self.budget.time_minutes * 60 - self.elapsed

    @property
    def remaining_tool_calls(self) -> int | None:
        return None if self.budget.tool_calls is None else self.budget.tool_calls - self.tool_calls_used

    def status(self) -> dict:
        return {
            "tool_calls_used": self.tool_calls_used,
            "patch_submitted": self.patch_submitted,
            "patch_size": len(self.submitted_patch),
            "tool_calls_remaining": self.remaining_tool_calls,
            "max_tool_calls": self.budget.tool_calls,
            "time_seconds_remaining": round(self.remaining_time, 1),
            "max_time_minutes": self.budget.time_minutes,
            "agent_elapsed_seconds": round(self.elapsed, 1),
            "max_turns": self.budget.turns,
            "command_timeout_seconds": self.limits.command_timeout_seconds,
        }

    # ----- gating -----
    def _gate(self, count: bool = True) -> dict | None:
        if self.remaining_time <= 0:
            return _err("BudgetExhausted", "Session time budget exhausted. Call submit_patch now.")
        if count:
            rem = self.remaining_tool_calls
            if rem is not None and rem <= 0:
                return _err("BudgetExhausted", f"Tool call budget exhausted ({self.tool_calls_used}/{self.budget.tool_calls}). Call submit_patch now.")
            self.tool_calls_used += 1
        return None

    def _finish(self, name: str, args: dict, result: dict) -> str:
        rem = self.remaining_tool_calls
        if self.budget.tool_calls is not None and self.tool_calls_used >= 20 and rem is not None and rem <= 10:
            result["budget_warning"] = f"Only {rem} tool call(s) remaining ({self.tool_calls_used}/{self.budget.tool_calls} used). Finalize your edits and call submit_patch soon."
        self.tool_log.append({"t": round(self.elapsed, 2), "tool": name, "args": args, "status": result.get("status", "ok")})
        return json.dumps(result, ensure_ascii=False)

    # ----- helpers -----
    def _resolve_path(self, filepath: str) -> str | dict:
        p = filepath.strip()
        if p.startswith(WORKSPACE + "/"):
            p = p[len(WORKSPACE) + 1:]
        elif p == WORKSPACE:
            p = ""
        p = p.lstrip("/")
        if ".." in p.split("/"):
            return _err("ValidationError", "path traversal ('..') is not allowed")
        return p

    def _read_remote(self, rel: str) -> tuple[bool, str]:
        r = self.sandbox.exec(f"cat -- {shlex.quote(WORKSPACE + '/' + rel)}", timeout=30)
        return r.exit_code == 0, r.stdout if r.exit_code == 0 else r.stderr

    def _truncate(self, s: str) -> tuple[str, bool]:
        n = self.limits.max_stdout_chars
        return (s[:n], True) if len(s) > n else (s, False)

    # ----- tool implementations -----
    def run_command(self, command: str) -> str:
        if (g := self._gate()):
            return self._finish("run_command", {"command": command}, g)
        timeout = min(self.limits.command_timeout_seconds, max(5, int(self.remaining_time)))
        r = self.sandbox.exec(command, timeout=timeout)
        out, _ = self._truncate(r.stdout)
        err, _ = self._truncate(r.stderr)
        if r.timed_out:
            res = _err("TimeoutExceeded", f"Command exceeded {timeout} seconds and was killed", stdout=out, stderr=err, timeout_seconds=timeout)
        elif r.exit_code == 0:
            res = {"status": "ok", "stdout": out, "exit_code": 0}
        else:
            res = _err("CommandError", f"Command failed with exit code {r.exit_code}", stdout=out, stderr=err, exit_code=r.exit_code)
        return self._finish("run_command", {"command": command}, res)

    def submit_patch(self) -> str:
        if self.remaining_time <= 0 and self.submitted_patch:
            return self._finish("submit_patch", {}, {"status": "ok", "patch_size": len(self.submitted_patch), "files_changed": self.submitted_patch.count("diff --git ")})
        patch = self.sandbox.extract_patch()
        self.submitted_patch = patch
        self.patch_submitted = True
        return self._finish("submit_patch", {}, {"status": "ok", "patch_size": len(patch), "files_changed": patch.count("diff --git ")})

    def get_status(self) -> str:
        return json.dumps(self.status())

    def read_file(self, filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
        args = {"filepath": filepath, "start_line": start_line, "end_line": end_line}
        if (g := self._gate()):
            return self._finish("read_file", args, g)
        rel = self._resolve_path(filepath)
        if isinstance(rel, dict):
            return self._finish("read_file", args, rel)
        ok, content = self._read_remote(rel)
        if not ok:
            return self._finish("read_file", args, _err("FileNotFound", f"could not read {rel}: {content.strip()[:300]}"))
        lines = content.split("\n")
        if content.endswith("\n"):
            lines = lines[:-1]
        total = len(lines)
        s = 1 if not start_line or start_line < 1 else start_line
        e = total if not end_line or end_line > total else end_line
        if s > total and total > 0:
            return self._finish("read_file", args, _err("ValidationError", f"start_line {s} exceeds total_lines {total}"))
        chunk = lines[s - 1:e]
        truncated = False
        if len(chunk) > self.limits.max_file_lines:
            chunk = chunk[: self.limits.max_file_lines]
            truncated = True
        text = "\n".join(chunk)
        if len(text) > self.limits.max_file_chars:
            cut = text[: self.limits.max_file_chars]
            text = cut[: cut.rfind("\n")] if "\n" in cut else cut
            chunk = text.split("\n")
            truncated = True
        res = {"status": "ok", "filepath": rel, "content": text, "start_line": s, "end_line": s + len(chunk) - 1 if chunk else s, "total_lines": total, "is_truncated": truncated}
        return self._finish("read_file", args, res)

    def edit_file(self, filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str:
        args = {"filepath": filepath, "old_len": len(old_string), "new_len": len(new_string), "allow_multiple": allow_multiple}
        if (g := self._gate()):
            return self._finish("edit_file", args, g)
        rel = self._resolve_path(filepath)
        if isinstance(rel, dict):
            return self._finish("edit_file", args, rel)
        ok, content = self._read_remote(rel)
        if not ok:
            return self._finish("edit_file", args, _err("FileEditError", f"file does not exist: {rel}"))
        if content == "":
            return self._finish("edit_file", args, _err("FileEditError", f"file is empty: {rel}; use write_file instead"))
        rr = apply_replacement(content, old_string, new_string, allow_multiple)
        if not rr.ok:
            return self._finish("edit_file", args, _err("FileEditError", rr.error, occurrences=rr.occurrences, strategy=rr.strategy))
        self.sandbox.write_text(WORKSPACE + "/" + rel, rr.content)
        import difflib
        diff = "".join(difflib.unified_diff(content.splitlines(True), rr.content.splitlines(True), f"a/{rel}", f"b/{rel}"))
        diff_t, trunc = self._truncate(diff)
        res = {"status": "ok", "filepath": rel, "occurrences": rr.occurrences, "strategy": rr.strategy, "diff": diff_t, "is_truncated": trunc}
        return self._finish("edit_file", args, res)

    def write_file(self, filepath: str, content: str) -> str:
        args = {"filepath": filepath, "size": len(content)}
        if (g := self._gate()):
            return self._finish("write_file", args, g)
        rel = self._resolve_path(filepath)
        if isinstance(rel, dict):
            return self._finish("write_file", args, rel)
        if not rel:
            return self._finish("write_file", args, _err("ValidationError", "filepath must not be empty"))
        self.sandbox.write_text(WORKSPACE + "/" + rel, content)
        return self._finish("write_file", args, {"status": "ok", "filepath": rel, "size": len(content.encode("utf-8"))})

    def get_code_neighbors(self, node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str:
        args = {"node": node, "edge_type": edge_type, "max_neighbors": max_neighbors}
        if (g := self._gate()):
            return self._finish("get_code_neighbors", args, g)
        if not self.graph.available:
            return self._finish("get_code_neighbors", args, _err("Unavailable", "no code graph for this repository"))
        return self._finish("get_code_neighbors", args, self.graph.neighbors(node, edge_type, max_neighbors))

    def search_similar_code(self, query: str, k: int = 10) -> str:
        args = {"query": query, "k": k}
        if (g := self._gate()):
            return self._finish("search_similar_code", args, g)
        if not self.graph.available:
            return self._finish("search_similar_code", args, _err("Unavailable", "no code embeddings for this repository"))
        return self._finish("search_similar_code", args, self.graph.similar(query, k))

    def get_code_subgraph(self, nodes: list[str]) -> str:
        args = {"nodes": nodes}
        if (g := self._gate()):
            return self._finish("get_code_subgraph", args, g)
        if not self.graph.available:
            return self._finish("get_code_subgraph", args, _err("Unavailable", "no code graph for this repository"))
        return self._finish("get_code_subgraph", args, self.graph.subgraph(nodes))

    # ----- registry -----
    def create_tools(self) -> dict[str, Callable]:
        """Return named ADK-ready functions (docstrings become tool descriptions)."""
        ctx = self

        def run_command(command: str) -> str:
            """Executes a shell command in /bin/bash -c inside /workspace. Returns JSON with stdout (5000-char cap) and exit_code."""
            return ctx.run_command(command)

        def submit_patch() -> str:
            """Captures git diff HEAD of /workspace as your final patch and ends the session after this turn. Call it last, after verifying your fix."""
            return ctx.submit_patch()

        def get_status() -> str:
            """Returns live budget consumption (tool calls, time remaining) and patch status. Free."""
            return ctx.get_status()

        def read_file(filepath: str, start_line: int | None = None, end_line: int | None = None) -> str:
            """Reads a file from /workspace with 1-indexed inclusive line slicing. Output is capped at 150 lines and 10000 characters."""
            return ctx.read_file(filepath, start_line, end_line)

        def edit_file(filepath: str, old_string: str, new_string: str, allow_multiple: bool = False) -> str:
            """Replaces old_string with new_string in an existing non-empty file inside /workspace. old_string must match exactly one location unless allow_multiple is true."""
            return ctx.edit_file(filepath, old_string, new_string, allow_multiple)

        def write_file(filepath: str, content: str) -> str:
            """Creates or overwrites a file at /workspace/<filepath>, creating parent directories."""
            return ctx.write_file(filepath, content)

        def get_code_neighbors(node: str, edge_type: str | None = None, max_neighbors: int = 50) -> str:
            """Finds incoming and outgoing neighbors (callers, callees, imports) of a symbol in the repository call/dependency graph."""
            return ctx.get_code_neighbors(node, edge_type, max_neighbors)

        def search_similar_code(query: str, k: int = 10) -> str:
            """Finds the top-k code symbols most similar to a given class, function, or module name using pre-computed embeddings. Pass a symbol name, not a sentence."""
            return ctx.search_similar_code(query, k)

        def get_code_subgraph(nodes: list[str]) -> str:
            """Extracts the induced subgraph (nodes and interconnecting edges) for a list of symbols."""
            return ctx.get_code_subgraph(nodes)

        return {
            "run_command": run_command, "submit_patch": submit_patch, "get_status": get_status,
            "read_file": read_file, "edit_file": edit_file, "write_file": write_file,
            "get_code_neighbors": get_code_neighbors, "search_similar_code": search_similar_code, "get_code_subgraph": get_code_subgraph,
        }
