"""swelite CLI: eval, verify-gold, verify-null, build-image, validate."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import asdict
from pathlib import Path

import typer
from rich.console import Console

from .compile import ModelRegistry, load_eval_config, validate_directory
from .sandbox import build_image as _build_image
from .tasks import DataDir, load_tasks
from .tools import Budget, HarnessLimits
from .verify import verify_task

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


def _select(data: DataDir, task_ids: list[str] | None, shard_index: int, num_shards: int, limit: int | None):
    tasks = load_tasks(data.tasks_path, set(task_ids) if task_ids else None)
    tasks = [t for i, t in enumerate(tasks) if i % num_shards == shard_index]
    return tasks[:limit] if limit else tasks


def _write_jsonl(path: Path, row: dict) -> None:
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, default=str) + "\n")


def _summarize(results_dir: Path) -> dict:
    rows = [json.loads(l) for l in (results_dir / "task_results.jsonl").read_text().splitlines() if l.strip()]
    by_repo: dict[str, dict] = {}
    for r in rows:
        d = by_repo.setdefault(r["repo"], {"total": 0, "resolved": 0})
        d["total"] += 1
        d["resolved"] += int(bool(r.get("resolved")))
    resolved = sum(int(bool(r.get("resolved"))) for r in rows)
    summary = {
        "total": len(rows), "resolved": resolved,
        "resolution_rate": (resolved / len(rows)) if rows else 0.0,
        "by_repo": by_repo,
        "errors": [{"id": r["instance_id"], "error": r.get("agent_error") or r.get("verify_error")} for r in rows if r.get("agent_error") or r.get("verify_error")],
        "mean_elapsed_seconds": (sum(r.get("elapsed_seconds", 0) for r in rows) / len(rows)) if rows else 0,
    }
    (results_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


@app.command("build-image")
def build_image(data_dir: Path = typer.Option(..., "--data-dir"), tag: str = "swebench-sandbox:latest"):
    """Build the sandbox image from the dataset's Dockerfile.public + wheels."""
    _build_image(DataDir(data_dir), tag=tag)


@app.command()
def validate(submission_dir: Path):
    """Structural validation of a submission directory (no model needed)."""
    from .compile import Compiler
    from .tools import SwegemmaContext
    problems = validate_directory(submission_dir)
    try:
        names = ["run_command", "submit_patch", "get_status", "read_file", "edit_file", "write_file", "get_code_neighbors", "search_similar_code", "get_code_subgraph"]
        dummy = {n: (lambda *a, **k: "{}") for n in names}
        for n, f in dummy.items():
            f.__name__ = n
        Compiler(submission_dir, dummy, ModelRegistry()).compile()
    except Exception as e:
        problems.append(f"compile: {e}")
    if problems:
        for p in problems:
            console.print(f"[red]x[/red] {p}")
        raise typer.Exit(1)
    console.print("[green]ok[/green] submission compiles")
    console.print(load_eval_config(submission_dir))


@app.command("verify-gold")
def verify_gold(
    data_dir: Path = typer.Option(..., "--data-dir"),
    results_dir: Path = typer.Option(Path("results/gold"), "--results-dir"),
    task_ids: list[str] = typer.Option(None, "--task-id"),
    concurrency: int = 2, shard_index: int = 0, num_shards: int = 1, limit: int = None,
    null: bool = typer.Option(False, "--null", help="Apply no agent patch (expect failures) instead of the gold patch"),
    image: str = "swebench-sandbox:latest",
):
    """Harness self-check: gold patch must pass (or, with --null, the bare test_patch must fail)."""
    data = DataDir(data_dir)
    tasks = _select(data, task_ids, shard_index, num_shards, limit)
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "test_outputs").mkdir(exist_ok=True)
    sem = asyncio.Semaphore(concurrency)

    async def one(t):
        async with sem:
            t0 = time.monotonic()
            vr = await asyncio.to_thread(verify_task, t, data, "" if null else t.patch, image)
            (results_dir / "test_outputs" / f"{t.instance_id}.log").write_text(vr.output)
            row = {"instance_id": t.instance_id, "repo": t.repo, "resolved": vr.resolved, "exit_code": vr.exit_code, "verify_error": vr.error, "elapsed_seconds": round(time.monotonic() - t0, 1)}
            _write_jsonl(results_dir / "task_results.jsonl", row)
            mark = "[green]PASS[/green]" if vr.resolved else "[red]FAIL[/red]"
            console.print(f"{mark} {t.instance_id} exit={vr.exit_code} {vr.error[:120]} ({row['elapsed_seconds']}s)")

    async def main():
        await asyncio.gather(*(one(t) for t in tasks))

    asyncio.run(main())
    s = _summarize(results_dir)
    console.print(json.dumps({k: v for k, v in s.items() if k != "errors"}, indent=2))


@app.command()
def eval(
    data_dir: Path = typer.Option(..., "--data-dir"),
    submission_dir: Path = typer.Option(..., "--submission-dir"),
    results_dir: Path = typer.Option(..., "--results-dir"),
    api_base: str = "http://127.0.0.1:8000/v1",
    served_model: str = typer.Option(None, help="Model name the local server exposes (e.g. a 12B proxy). Defaults to the alias in agent.yaml."),
    task_ids: list[str] = typer.Option(None, "--task-id"),
    concurrency: int = 1, shard_index: int = 0, num_shards: int = 1, limit: int = None,
    max_tool_calls: int = typer.Option(None), max_time_minutes: float = typer.Option(None), max_turns: int = typer.Option(None),
    command_timeout: int = typer.Option(None),
    image: str = "swebench-sandbox:latest",
    skip_verify: bool = False,
):
    """Run a submission against tasks (Phase 1) and verify patches (Phase 2)."""
    data = DataDir(data_dir)
    problems = validate_directory(submission_dir)
    if problems:
        for p in problems:
            console.print(f"[red]x[/red] {p}")
        raise typer.Exit(1)
    ec = load_eval_config(submission_dir)
    budget = Budget(
        time_minutes=float(max_time_minutes or ec.get("max_time_minutes") or 60.0),
        tool_calls=(max_tool_calls or ec.get("max_tool_calls")),
        turns=(max_turns or ec.get("max_turns") or 500),
    )
    limits = HarnessLimits(command_timeout_seconds=int(command_timeout or ec.get("timeout_seconds") or 300))
    registry = ModelRegistry(api_base=api_base, served_model=served_model)
    tasks = _select(data, task_ids, shard_index, num_shards, limit)
    for sub in ("patches", "test_outputs", "traces", "logs"):
        (results_dir / sub).mkdir(parents=True, exist_ok=True)
    (results_dir / "config.json").write_text(json.dumps({"budget": asdict(budget), "limits": asdict(limits), "submission_dir": str(submission_dir), "api_base": api_base, "served_model": served_model, "n_tasks": len(tasks)}, indent=2))
    console.print(f"{len(tasks)} tasks, budget={budget}, limits={limits}")
    sem = asyncio.Semaphore(concurrency)

    from .runner import run_agent_sandbox

    async def one(t):
        async with sem:
            t0 = time.monotonic()
            rr = await run_agent_sandbox(t, data, submission_dir, registry, budget, limits, image=image, log_path=results_dir / "logs" / f"{t.instance_id}.log")
            (results_dir / "patches" / f"{t.instance_id}.patch").write_text(rr.agent_patch)
            trace = {k: v for k, v in asdict(rr).items() if k != "agent_patch"}
            (results_dir / "traces" / f"trace_{t.instance_id}.json").write_text(json.dumps(trace, default=str))
            row = {"instance_id": t.instance_id, "repo": t.repo, "patch_submitted": rr.patch_submitted, "patch_size": len(rr.agent_patch),
                   "tool_calls": rr.tool_calls, "llm_turns": rr.llm_turns, "nudges": rr.nudges, "agent_error": rr.agent_error,
                   "agent_seconds": round(rr.elapsed_seconds, 1), "setup_seconds": round(rr.setup_seconds, 1)}
            if skip_verify:
                row["resolved"] = None
            elif rr.agent_patch.strip():
                vr = await asyncio.to_thread(verify_task, t, data, rr.agent_patch, image)
                (results_dir / "test_outputs" / f"{t.instance_id}.log").write_text(vr.output)
                row.update({"resolved": vr.resolved, "exit_code": vr.exit_code, "verify_error": vr.error})
            else:
                row.update({"resolved": False, "exit_code": None, "verify_error": "empty patch"})
            row["elapsed_seconds"] = round(time.monotonic() - t0, 1)
            _write_jsonl(results_dir / "task_results.jsonl", row)
            mark = "[green]RESOLVED[/green]" if row.get("resolved") else "[red]failed[/red]"
            console.print(f"{mark} {t.instance_id} calls={rr.tool_calls} turns={rr.llm_turns} submitted={rr.patch_submitted} patch={len(rr.agent_patch)}B err={rr.agent_error[:100]} ({row['elapsed_seconds']}s)")

    async def main():
        await asyncio.gather(*(one(t) for t in tasks))

    asyncio.run(main())
    s = _summarize(results_dir)
    console.print(json.dumps({k: v for k, v in s.items() if k != "errors"}, indent=2))


if __name__ == "__main__":
    app()
