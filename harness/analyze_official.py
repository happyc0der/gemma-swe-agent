#!/usr/bin/env python3
"""Summarize a results directory produced by the official `swegemma eval` (task_results.jsonl + logs/).

Usage: python3 harness/analyze_official.py <results_dir> [<results_dir> ...]
"""
import collections
import json
import re
import sys
from pathlib import Path

ANSI = re.compile(r"\x1b\[[0-9;]*m")
TOOL_RE = re.compile(r"^\s*\[\s*[\d.]+s\]\s+\S+\s+(run_command|read_file|edit_file|write_file|get_status|submit_patch|get_code_neighbors|search_similar_code|get_code_subgraph|code_analyzer)\b")


def analyze(d: Path) -> dict:
    rows = [json.loads(l) for l in (d / "task_results.jsonl").open()] if (d / "task_results.jsonl").exists() else []
    out = {"dir": d.name, "tasks": len(rows), "resolved": sum(1 for r in rows if r.get("resolved")),
           "patch": sum(1 for r in rows if r.get("agent_patch_size", 0) > 0),
           "mean_tool_calls": round(sum(r.get("tool_calls", 0) for r in rows) / len(rows), 1) if rows else 0,
           "mean_seconds": round(sum(r.get("duration_seconds", 0) for r in rows) / len(rows)) if rows else 0}
    errs = collections.Counter((r.get("error") or "none")[:50] for r in rows)
    out["errors"] = dict(errs.most_common(6))
    tools = collections.Counter(); terr = collections.Counter(); nudges = 0; submits = 0; overflow = 0
    for f in sorted((d / "logs").glob("*.log")) if (d / "logs").exists() else []:
        txt = ANSI.sub("", f.read_text(errors="replace"))
        for line in txt.splitlines():
            m = TOOL_RE.match(line)
            if m:
                tools[m.group(1)] += 1
            m2 = re.search(r"'error_type': '(\w+)'", line)
            if m2:
                terr[m2.group(1)] += 1
        nudges += len(re.findall(r"Please continue your work|reached the token limit", txt))
        submits += 1 if "submit_patch" in txt else 0
        overflow += 1 if re.search(r"exceeds the available context|context window|ContextWindowExceeded|maximum context length", txt) else 0
    out["tool_calls_by_name"] = dict(tools.most_common())
    out["tool_errors"] = dict(terr.most_common())
    out["logs_with_submit_call"] = submits
    out["nudge_lines"] = nudges
    out["logs_with_context_overflow"] = overflow
    resolved_ids = [r["instance_id"] for r in rows if r.get("resolved")]
    out["resolved_ids"] = resolved_ids
    return out


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        print(json.dumps(analyze(Path(arg)), indent=1))
