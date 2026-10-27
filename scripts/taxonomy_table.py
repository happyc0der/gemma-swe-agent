"""Per-run occurrence counts of the failure modes in paper Section 4, from faithful-eval traces.
Usage: python3 scripts/taxonomy_table.py <label>=<run dir>:<max_tool_calls>[:<max_turns>] [...]
Prints one markdown row per run."""
import json,glob,sys
def content(o):
    if isinstance(o,str):
        try: o=json.loads(o)
        except Exception: return {}
    c=o.get('content') if isinstance(o,dict) else None
    if isinstance(c,str):
        try: return json.loads(c)
        except Exception: return {}
    return c or {}
print('| run | resolved | agent min | edit_file calls (missing old_string) | run_command calls | no-match greps (exact repeats) | exact repeated calls | `submit_patch` in shell | tasks at call cap | tasks at turn cap | empty patches |')
print('|---|---|---|---|---|---|---|---|---|---|---|')
for arg in sys.argv[1:]:
    label,rest=arg.split('=',1); parts=rest.split(':'); run=parts[0]; cap=int(parts[1]); turns=int(parts[2]) if len(parts)>2 else 80
    rs={}
    for p in glob.glob(run+'/**/task_results.jsonl',recursive=True):
        for l in open(p): r=json.loads(l); rs[r['instance_id']]=r
    ed=edmiss=rc=nm=nmrep=rep=sp=0
    for f in sorted(glob.glob(run+'/**/traces/trace_*.json',recursive=True)):
        seen=set(); nmseen=set()
        for s in json.load(open(f))['steps']:
            c0=content(s.get('observation'))
            for c in s.get('tool_calls') or []:
                a=c.get('arguments') if isinstance(c.get('arguments'),dict) else {}
                key=(c['function_name'],json.dumps(a,sort_keys=True))
                if key in seen: rep+=1
                seen.add(key)
                if c['function_name']=='edit_file':
                    ed+=1; edmiss+=not a.get('old_string')
                if c['function_name']=='run_command':
                    rc+=1; cmd=a.get('command','')
                    if 'submit_patch' in cmd: sp+=1
                    det=c0.get('details') or {}
                    if c0.get('status')=='error' and det.get('exit_code')==1 and not det.get('stdout') and not det.get('stderr') and 'grep' in cmd:
                        nm+=1; nmrep+=cmd in nmseen; nmseen.add(cmd)
    v=list(rs.values())
    print(f"| {label} | {sum(bool(r.get('resolved')) for r in v)}/{len(v)} | {sum(r.get('duration_seconds') or 0 for r in v)/60:.0f} | {ed} ({edmiss}) | {rc} | {nm} ({nmrep}) | {rep} | {sp} | "
          f"{sum((r.get('tool_calls') or 0)>=cap for r in v)} | {sum((r.get('total_llm_calls') or 0)>=turns for r in v)} | {sum(r.get('agent_patch_size',1)==0 for r in v)} |")
