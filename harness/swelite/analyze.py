"""Failure taxonomy for a swelite results directory (experiments/README.md buckets)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


def classify(row: dict, trace: dict | None) -> tuple[str, dict]:
    """Return (bucket, stats) for one task."""
    calls = [x for x in (trace or {}).get("tool_log", [])]
    names = [c["tool"] for c in calls]
    args = [json.dumps(c.get("args"), sort_keys=True) for c in calls]
    repeats = sum(1 for i in range(1, len(args)) if args[i] == args[i - 1])
    max_run = 1
    run = 1
    for i in range(1, len(args)):
        run = run + 1 if args[i] == args[i - 1] else 1
        max_run = max(max_run, run)
    edit_err = sum(1 for c in calls if c["tool"] in ("edit_file", "write_file") and c.get("status") == "error")
    edit_ok = sum(1 for c in calls if c["tool"] in ("edit_file", "write_file") and c.get("status") == "ok")
    stats = {"calls": len(calls), "repeats": repeats, "max_identical_run": max_run, "edit_ok": edit_ok, "edit_err": edit_err,
             "reads": names.count("read_file"), "cmds": names.count("run_command"), "graph": sum(names.count(n) for n in ("get_code_neighbors", "search_similar_code", "get_code_subgraph"))}
    if row.get("resolved"):
        return "resolved", stats
    err = (row.get("agent_error") or "") + " " + (row.get("verify_error") or "")
    if "Failed to apply" in err:
        return "apply_failed", stats
    if row.get("patch_size", 0) > 0:
        return "broke_tests", stats
    # empty patch: why?
    if max_run >= 3 or repeats >= len(calls) * 0.3:
        return "loop", stats
    if edit_err and not edit_ok:
        return "edit_mismatch", stats
    if "budget" in err or "exhausted" in err or "nudges" in err:
        return "budget", stats
    return "no_patch", stats


def analyze(results_dir: Path) -> dict:
    rows = [json.loads(l) for l in (results_dir / "task_results.jsonl").read_text().splitlines() if l.strip()]
    buckets: Counter = Counter()
    per_task = []
    agg = Counter()
    for r in rows:
        tp = results_dir / "traces" / f"trace_{r['instance_id']}.json"
        trace = json.loads(tp.read_text()) if tp.exists() else None
        b, st = classify(r, trace)
        buckets[b] += 1
        per_task.append({"id": r["instance_id"], "bucket": b, **st, "seconds": r.get("agent_seconds")})
        for k, v in st.items():
            agg[k] += v
    n = len(rows) or 1
    return {"n": len(rows), "resolved": buckets.get("resolved", 0), "resolution_rate": round(buckets.get("resolved", 0) / n, 3),
            "buckets": dict(buckets.most_common()), "mean": {k: round(v / n, 1) for k, v in agg.items()},
            "per_task": per_task}


def main(results_dir: str, show: int = 12) -> None:
    a = analyze(Path(results_dir))
    print(json.dumps({k: v for k, v in a.items() if k != "per_task"}, indent=1))
    for t in a["per_task"][:show]:
        print(f"  {t['id']:18s} {t['bucket']:14s} calls={t['calls']:3d} repeats={t['repeats']:3d} maxrun={t['max_identical_run']:2d} edits ok/err={t['edit_ok']}/{t['edit_err']} s={t['seconds']}")
    (Path(results_dir) / "taxonomy.json").write_text(json.dumps(a, indent=1))


if __name__ == "__main__":
    import sys
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 12)
