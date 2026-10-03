"""Compare faithful-eval runs task by task from their official-harness traces.

Usage: python3 scripts/faithful_metrics.py RESULTS_DIR [RESULTS_DIR ...]
Each RESULTS_DIR is an unpacked `faithful-<variant>` folder (task_results.jsonl + traces/trace_<id>.json).

Per run: solved, tasks with no source edit, exact repeat calls, repeat searches of a term that already came back
empty, consecutive chunk reads of one file (paging), session timeouts, steps with text before the call (notes),
prose-only steps (no tool call), output tokens per step, and total agent time.
"""
import glob
import json
import os
import re
import statistics
import sys


def empty_search(cmd, obs):
    if not re.match(r"\s*(grep|rg|find)\b", cmd):
        return False
    try:
        o = json.loads(obs)
    except Exception:
        return False
    out = o.get("stdout")
    if out is None:
        out = (o.get("details") or {}).get("stdout", "")
    return not (out or "").strip()


def term(cmd):
    m = re.search(r"grep\s+(?:-[A-Za-z]+\s+)*(?:\"([^\"]+)\"|'([^']+)'|(\S+))", cmd)
    return (m.group(1) or m.group(2) or m.group(3)) if m else None


def task_metrics(trace):
    steps = [s for s in trace["steps"] if s.get("source") == "agent"]
    calls, dead, first_edit, notes, prose, toks = [], {}, None, 0, 0, []
    run = best = 0
    prev_file = None
    for s in steps:
        tcs = s.get("tool_calls") or []
        toks.append((s.get("metrics") or {}).get("completion_tokens") or 0)
        if not tcs:
            prose += 1
            continue
        if (s.get("message") or "").strip():
            notes += 1
        obs = (s.get("observation") or {}).get("content", "") or ""
        for tc in tcs:
            a = tc["arguments"] if isinstance(tc["arguments"], dict) else {}
            fn, cmd = tc["function_name"], a.get("command", "") or ""
            calls.append((fn, json.dumps(a, sort_keys=True)))
            if first_edit is None and (fn in ("edit_file", "write_file") or (fn == "run_command" and "fix.py" in cmd and "python3 /tmp/fix.py" in cmd)):
                first_edit = len(calls)
            if fn == "run_command" and empty_search(cmd, obs):
                t = term(cmd)
                if t:
                    dead[t] = dead.get(t, 0) + 1
            m = re.match(r"\s*sed -n '?(\d+),(\d+)p'? (\S+)\s*$", cmd) if fn == "run_command" else None
            if m:
                run = run + 1 if prev_file == m.group(3) else 1
                prev_file = m.group(3)
            else:
                run, prev_file = 0, None
            best = max(best, run)
    return dict(calls=len(calls), dups=len(calls) - len(set(calls)), dead_repeats=sum(n - 1 for n in dead.values() if n > 1),
                first_edit=first_edit, paging=best, notes=notes, prose=prose, steps=len(steps),
                tok_median=statistics.median(toks) if toks else 0)


def run_metrics(rdir):
    res = {}
    for line in open(os.path.join(rdir, "task_results.jsonl")):
        r = json.loads(line)
        res[r["instance_id"]] = r
    per = {}
    for f in glob.glob(os.path.join(rdir, "traces", "trace_*.json")):
        iid = os.path.basename(f)[len("trace_"):-len(".json")]
        per[iid] = task_metrics(json.load(open(f)))
    return res, per


def main(dirs):
    runs = [(os.path.basename(d.rstrip("/")), *run_metrics(d)) for d in dirs]
    ids = sorted(set().union(*(r[1].keys() for r in runs)))
    print(f"{'task':16s} " + " | ".join(f"{n[:22]:22s}" for n, _, _ in runs))
    for iid in ids:
        cells = []
        for _, res, per in runs:
            r, m = res.get(iid, {}), per.get(iid)
            if not m:
                cells.append(f"{'-':22s}")
                continue
            to = "T" if "timeout" in (r.get("error") or "") else " "
            cells.append(f"{'S' if r.get('resolved') else '.'}{to} c={m['calls']:2d} e@{str(m['first_edit']):4s} d={m['dups']:2d}")
        print(f"{iid:16s} " + " | ".join(cells))
    print()
    for name, res, per in runs:
        ms = list(per.values())
        fe = sorted(m["first_edit"] or 99 for m in ms)
        print(f"{name}: solved {sum(r['resolved'] for r in res.values())}/{len(res)}"
              f" | no-edit {sum(m['first_edit'] is None for m in ms)}"
              f" | exact repeats {sum(m['dups'] for m in ms)} of {sum(m['calls'] for m in ms)} calls"
              f" | dead-term repeats {sum(m['dead_repeats'] for m in ms)}"
              f" | paging>=4 {sum(m['paging'] >= 4 for m in ms)} tasks"
              f" | session timeouts {sum('timeout' in (r.get('error') or '') for r in res.values())}"
              f" | median first edit {fe[len(fe) // 2] if fe else '-'}"
              f" | steps with a note {sum(m['notes'] for m in ms)}/{sum(m['steps'] for m in ms)}"
              f" | prose-only steps {sum(m['prose'] for m in ms)}"
              f" | median output tokens/step {statistics.median([m['tok_median'] for m in ms]) if ms else 0}"
              f" | agent time {sum(r.get('duration_seconds') or 0 for r in res.values()) / 60:.0f} min")


if __name__ == "__main__":
    main(sys.argv[1:])
