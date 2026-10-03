# Kaggle CPU kernel: validate the faithful (scorer-like) subprocess sandbox before spending GPU hours.
# Runs the OFFICIAL swegemma verify_task on holdout tasks with the gold patch (should pass) and with no patch
# (should fail), using kaggle/faithful_sandbox.py, and times the per-task setup. No model involved.
import asyncio, glob, json, os, pathlib, subprocess, sys, time
T0 = time.time()
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None):
    log("$", cmd[:200]); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout[-1500:] + ("\n" + r.stderr[-1500:] if r.stderr.strip() else "")).strip()
    if out: log(out)
    return r
def first(pattern):
    hits = sorted(glob.glob(pattern, recursive=True)); return hits[0] if hits else None

tasks_file = first("/kaggle/input/**/tasks.jsonl"); assert tasks_file, "competition data not attached"
DATA = pathlib.Path(tasks_file).parent
WH = pathlib.Path(first("/kaggle/input/**/swegemma-*.whl")).parent
def wheel(prefix):
    """Find a wheelhouse file by normalized name prefix (Kaggle may rename uploaded files)."""
    norm = lambda s: s.lower().replace("-", "_")
    c = sorted(p for p in WH.glob("*.whl") if norm(p.name).startswith(norm(prefix)))
    assert c, f"no wheel for {prefix}: {sorted(p.name for p in WH.glob('*.whl'))}"
    return str(c[-1])
log("DATA", DATA, "| WHEELHOUSE", WH); sh("python3 --version; nproc; free -g | head -2; df -h / /tmp | tail -2")

# Official harness (pure-python wheels from the organizers' wheelhouse; dependencies from PyPI).
sh("ls " + str(WH) + " | head -60")
sh(f"python3 -m pip install -q {wheel('google_genai')} {wheel('google_adk')} 2>&1 | tail -2", timeout=1800)
sh(f"python3 -m pip install -q --no-deps {wheel('swegemma')} {wheel('adk_submission')} {wheel('adk_eval_core')}", timeout=600)
sh("python3 -c 'import swegemma, adk_submission, google.adk; print(\"harness ok\", google.adk.__version__)'")
sh("python3 -m pip install -q litellm docker networkx cachetools python-dotenv 2>&1 | tail -2", timeout=1800)
sh("cd /kaggle/working && rm -rf gemma-swe-agent && git clone -q https://github.com/happyc0der/gemma-swe-agent.git && cd gemma-swe-agent && git log --oneline | head -1")
REPO = pathlib.Path("/kaggle/working/gemma-swe-agent")
sys.path.insert(0, str(REPO / "kaggle"))
import logging; logging.basicConfig(level=logging.WARNING)
import faithful_sandbox as fs
info = fs.prepare_host(DATA); log("prepare_host:", json.dumps(info))
fs.apply()

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
from swegemma.config import EvalConfig
from swegemma.models import load_tasks
from swegemma.models.registry import setup_gemma_model_registry
from swegemma.sandbox import SubprocessManager
from swegemma.harness.verification import verify_task
from swegemma.deduplication import resolve_task_snapshot_paths

splits = json.loads((REPO / "experiments/splits.json").read_text())
ids = [t for t in splits["holdout"] if t not in set(splits["env_unstable"])]
tasks = {t.instance_id: t for t in load_tasks(pathlib.Path(tasks_file))}
cfg = EvalConfig(tasks_path=pathlib.Path(tasks_file), snapshots_dir=DATA / "snapshots", results_dir=pathlib.Path("/kaggle/working/results"),
                 submission_dir=REPO / "submission", models=setup_gemma_model_registry(api_base="http://127.0.0.1:1/v1"),
                 sandbox="subprocess", timeout_seconds=180, wheels_dir=DATA / "wheels", graph_dir=str(DATA / "graphs"),
                 embeddings_dir=str(DATA / "embeddings"), display_mode="quiet")
mgr = SubprocessManager(timeout_seconds=180)
rows = []
for iid in ids:
    t = tasks[iid]
    snap, base, patch = resolve_task_snapshot_paths(cfg.snapshots_dir, iid, t.repo)
    kw = {"base_snapshot_path": base, "patch_path": patch} if base else {}
    out = {"id": iid}
    for kind, p in (("gold", t.patch), ("null", "")):
        s = time.time()
        try:
            r = asyncio.run(verify_task(mgr, cfg, t, snap, agent_patch=p, start_time=s, **kw))
            out[kind] = bool(r.resolved); out[kind + "_s"] = round(time.time() - s, 1); out[kind + "_err"] = (r.error or "")[:160]
            if kind == "gold" and not r.resolved: out["gold_tail"] = (r.test_output or "")[-600:]
        except Exception as e:
            out[kind] = None; out[kind + "_err"] = f"{type(e).__name__}: {e}"[:300]
    rows.append(out); log(json.dumps({k: v for k, v in out.items() if k != "gold_tail"}))
gold = sum(1 for r in rows if r.get("gold")); null = sum(1 for r in rows if r.get("null"))
log(f"SUMMARY gold {gold}/{len(rows)} (want all) | null {null}/{len(rows)} (want 0) | mean gold verify {sum(r.get('gold_s',0) for r in rows)/len(rows):.0f}s | total {(time.time()-T0)/60:.0f} min")
json.dump(rows, open("/kaggle/working/env_check.json", "w"), indent=1)
log("RUN_DONE")
