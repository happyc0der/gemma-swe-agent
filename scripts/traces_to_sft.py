"""Turn resolved official-harness traces into chat-format SFT examples (the 31B's own successful trajectories).

Usage: python3 scripts/traces_to_sft.py OUT.jsonl RESULTS_DIR [RESULTS_DIR ...] [--exclude-holdout]

Each line of OUT.jsonl: {"instance_id", "source", "messages": [...]} in OpenAI chat format (system, user, assistant
with tool_calls, tool), ready for tokenizer.apply_chat_template(messages, tools=...). Only resolved tasks are kept.
Rejected calls (malformed arguments) and exact repeats of an earlier call are dropped from the assistant side with
their observations, so the model is not trained on its own loops. --exclude-holdout drops the faithful-eval tasks
listed in experiments/splits.json so that eval stays clean.
"""
import glob
import json
import os
import sys


def convert(trace):
    msgs, seen, dropped = [], set(), 0
    for s in trace["steps"]:
        ev = (s.get("extra") or {}).get("event_type")
        if s.get("source") == "system" and ev == "system_instruction":
            msgs.append({"role": "system", "content": s["message"]})
        elif s.get("source") == "user":
            msgs.append({"role": "user", "content": s["message"]})
        elif s.get("source") == "agent":
            tcs = s.get("tool_calls") or []
            if not tcs:
                if (s.get("message") or "").strip() and "<|channel>" not in s["message"]:
                    msgs.append({"role": "assistant", "content": s["message"]})
                continue
            obs = (s.get("observation") or {}).get("content", "") or ""
            for tc in tcs:
                args = tc["arguments"] if isinstance(tc["arguments"], dict) else {}
                key = (tc["function_name"], json.dumps(args, sort_keys=True))
                if key in seen or "mandatory input parameters are not present" in obs:
                    dropped += 1
                    continue
                seen.add(key)
                cid = tc.get("tool_call_id") or f"call_{len(msgs)}"
                msgs.append({"role": "assistant", "content": "", "tool_calls": [
                    {"id": cid, "type": "function", "function": {"name": tc["function_name"], "arguments": json.dumps(args)}}]})
                msgs.append({"role": "tool", "tool_call_id": cid, "name": tc["function_name"], "content": obs})
    return msgs, dropped


def main(argv):
    out, dirs = argv[0], [a for a in argv[1:] if not a.startswith("--")]
    exclude = set()
    if "--exclude-holdout" in argv:
        exclude = set(json.load(open("experiments/splits.json"))["holdout"])
    n = kept = drops = 0
    with open(out, "w") as fo:
        for d in dirs:
            res = {json.loads(l)["instance_id"]: json.loads(l) for l in open(os.path.join(d, "task_results.jsonl"))}
            for f in sorted(glob.glob(os.path.join(d, "traces", "trace_*.json"))):
                iid = os.path.basename(f)[len("trace_"):-len(".json")]
                n += 1
                if not res.get(iid, {}).get("resolved") or iid in exclude:
                    continue
                msgs, dropped = convert(json.load(open(f)))
                drops += dropped
                if sum(m["role"] == "assistant" for m in msgs) < 2:
                    continue
                fo.write(json.dumps({"instance_id": iid, "source": os.path.basename(d.rstrip("/")), "messages": msgs}) + "\n")
                kept += 1
    print(f"{kept} examples from {n} traces ({drops} looping/malformed calls dropped) -> {out}")


if __name__ == "__main__":
    main(sys.argv[1:])
