"""Count no-match greps (exit 1, empty output, reported as status: error) in faithful-eval traces.
Usage: python3 scripts/count_nomatch_greps.py data/faithful_results/<run> [...]"""
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
for run in sys.argv[1:]:
    fs=sorted(glob.glob(run+'/**/traces/trace_*.json',recursive=True))
    rs={}
    for p in glob.glob(run+'/**/task_results.jsonl',recursive=True):
        for l in open(p): r=json.loads(l); rs[r['instance_id']]=r
    tot=nm=rep=0; tasks=set(); lost=0
    for f in fs:
        d=json.load(open(f)); iid=f.split('trace_')[-1][:-5]; seen=set()
        for s in d['steps']:
            c0=content(s.get('observation'))
            for c in s.get('tool_calls') or []:
                if c['function_name']!='run_command': continue
                cmd=(c.get('arguments') or {}).get('command','') if isinstance(c.get('arguments'),dict) else ''
                tot+=1
                det=c0.get('details') or {}
                if c0.get('status')=='error' and det.get('exit_code')==1 and not det.get('stdout') and not det.get('stderr') and 'grep' in cmd:
                    nm+=1; tasks.add(iid)
                    if cmd in seen: rep+=1
                    seen.add(cmd)
    emp={k for k,r in rs.items() if r.get('agent_patch_size',1)==0}
    uns={k for k,r in rs.items() if not r.get('resolved')}
    print(run.split('/')[0],'tasks',len(fs),'run_command',tot,'no-match greps',nm,'exact repeats',rep,'tasks with any',len(tasks),'| empty-patch tasks among them',len(emp&tasks),'of',len(emp),'| unresolved among them',len(uns&tasks))
