# Stage 2 of kaggle/eval_tpu/run.py, run inside the harness venv against the vLLM server on 127.0.0.1:8000.
# Same evaluation as kaggle/eval_faithful/run.py (official Evaluator, faithful sandbox, holdout subset, sequential tasks),
# but the variants keep their thinking settings and max_time_minutes is scaled by CFG["time_scale"] from the measured
# decode speed. Usage: python eval_stage.py '<json cfg>'
import asyncio, glob, json, os, pathlib, subprocess, sys, time
CFG = json.loads(sys.argv[1]); T0 = CFG["t0"]
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + "[stage2] " + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None):
    log("$", cmd[:220]); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout[-1500:] + ("\n" + r.stderr[-1500:] if r.stderr.strip() else "")).strip()
    if out: log(out)
    return r
def first(pattern):
    hits = sorted(glob.glob(pattern, recursive=True)); return hits[0] if hits else None

tasks_file = first("/kaggle/input/**/tasks.jsonl"); assert tasks_file, "competition data not attached"
DATA = pathlib.Path(tasks_file).parent; WH = pathlib.Path(first("/kaggle/input/**/swegemma-*.whl")).parent
def wheel(prefix):
    norm = lambda s: s.lower().replace("-", "_")
    c = sorted(p for p in WH.glob("*.whl") if norm(p.name).startswith(norm(prefix)))
    assert c, f"no wheel for {prefix}"
    return str(c[-1])
sh(f"python3 -m pip install -q {wheel('google_genai')} {wheel('google_adk')} 2>&1 | tail -2", timeout=1800)
sh(f"python3 -m pip install -q --no-deps {wheel('swegemma')} {wheel('adk_submission')} {wheel('adk_eval_core')}", timeout=600)
sh("python3 -m pip install -q litellm docker networkx cachetools python-dotenv huggingface_hub pyyaml 2>&1 | tail -2", timeout=1800)
REPO = pathlib.Path("/kaggle/working/gemma-swe-agent"); sys.path.insert(0, str(REPO / "kaggle"))
import logging; logging.basicConfig(level=logging.WARNING)
import faithful_sandbox as fs
log("prepare_host:", json.dumps(fs.prepare_host(DATA))); fs.apply()

os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm, yaml
litellm.drop_params = True
from adk_submission import ModelRegistry, discover_adapters
from google.adk.models.lite_llm import LiteLlm
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator
from swegemma.models import load_tasks
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
import swegemma; log("swegemma version", getattr(swegemma, "__version__", "?"))
NAME = "gemma-4-31b-it-qat-w4a16-ct"; API = "http://127.0.0.1:8000/v1"

splits = json.loads((REPO / "experiments/splits.json").read_text())
hold = [t for t in splits["holdout"] if t not in set(splits["env_unstable"])]
tasks = {t.instance_id: t for t in load_tasks(pathlib.Path(tasks_file))}
subset, per = [], {}
for iid in hold:
    r = tasks[iid].repo
    if per.get(r, 0) < CFG["n_per_repo"].get(r, 0): subset.append(iid); per[r] = per.get(r, 0) + 1
if CFG.get("subset") == "B":
    subset = [iid for iid in hold if iid not in set(subset)]
elif CFG.get("subset") == "AB":
    subset = subset + [iid for iid in hold if iid not in set(subset)]
elif CFG.get("subset") == "DEV":   # 33 stable dev tasks (fastapi 19, rich 12, requests 1, httpx 1): a third, unused eval set
    quota = {"fastapi": 19, "rich": 12, "requests": 1, "httpx": 1}; subset = []
    for iid in (t for t in splits["dev"] if t not in set(splits["env_unstable"])):
        if quota.get(iid.split("_")[0], 0) > 0: subset.append(iid); quota[iid.split("_")[0]] -= 1
log("subset", len(subset), per, "time_scale", CFG["time_scale"])

def make_cfg(sub, results_dir, ids):
    ev = yaml.safe_load((sub / "eval_config.yaml").read_text()); ev = ev.get("evaluation", ev)
    adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    reg = ModelRegistry(); reg.register(NAME, LiteLlm(model=f"openai/{NAME}", api_base=API, api_key="EMPTY", num_retries=5))
    for name in (getattr(adapters, "adapters", None) or {}):
        reg.register(name, LiteLlm(model=f"openai/{name}", api_base=API, api_key="EMPTY", num_retries=5))
    limits, gen = build_submission_limits()
    return ev, EvalConfig(tasks_path=pathlib.Path(tasks_file), snapshots_dir=DATA / "snapshots", results_dir=results_dir,
                      submission_dir=sub, models=reg, sandbox="subprocess", timeout_seconds=ev.get("timeout_seconds"),
                      max_time_minutes=float(ev["max_time_minutes"]) * CFG["time_scale"], max_tool_calls=ev.get("max_tool_calls"),
                      max_turns=ev.get("max_turns"), limits=limits, generation_constraints=gen, adapter_manifest=adapters,
                      context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
                      events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5),
                      graph_dir=str(DATA / "graphs"), embeddings_dir=str(DATA / "embeddings"), wheels_dir=DATA / "wheels",
                      task_ids=ids, concurrency=1, display_mode="quiet")
def step_stats(results_dir):
    toks = sorted((s.get("metrics") or {}).get("completion_tokens") or 0 for f in glob.glob(f"{results_dir}/traces/*.json")
                  for s in json.load(open(f))["steps"] if s.get("source") == "agent")
    return {"steps": len(toks), "median_out_tokens": toks[len(toks) // 2] if toks else -1, "p90_out_tokens": toks[int(len(toks) * 0.9)] if toks else -1}

# Canary: the thinking-on base on an easy task (thinking-off twins solve it in 4-7 calls).
sub0 = REPO / "experiments/variants/pub-budget-fit"
_, c0 = make_cfg(sub0, pathlib.Path("/kaggle/working/results/canary"), ["fastapi_14303"])
t = time.time(); can = asyncio.run(Evaluator(c0).run())
log(f"CANARY fastapi_14303 (thinking on): resolved {can.resolved}/{can.total} in {time.time()-t:.0f}s", step_stats("/kaggle/working/results/canary"))
if can.resolved != 1: log("CANARY FAILED: stopping before the main runs"); sys.exit(1)

for rel in CFG["variants"]:
    if (time.time() - T0) / 3600 > CFG["session_budget_h"] - 3.0: log("SKIP", rel, "(session budget)"); continue
    sub = REPO / rel; name = "tpu-" + pathlib.Path(rel).name + ({"B": "-setB", "AB": "-setAB", "DEV": "-setDEV"}.get(CFG.get("subset"), ""))
    rd = pathlib.Path(f"/kaggle/working/results/{name}")
    ev, cfg = make_cfg(sub, rd, subset)
    log(f"RUN {name}: eval={ev} scaled time={cfg.budget.time_minutes} min, {len(subset)} tasks")
    t = time.time(); res = asyncio.run(Evaluator(cfg).run())
    log(f"RUN_DONE {name}: resolved {res.resolved}/{res.total} in {(time.time()-t)/60:.0f} min", step_stats(rd))
    sh(f"cd /kaggle/working/results && tar -czf /kaggle/working/{name}.tgz {name}")
log(f"stage 2 done after {(time.time()-T0)/3600:.2f} h")
