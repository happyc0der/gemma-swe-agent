# Kaggle 4x L4 (the scorer's hardware): evaluate submission configs with the OFFICIAL stack, i.e. the wheelhouse's
# vLLM 0.19.1 (TP=4, flags copied from the organizers' Getting Started notebook) + swegemma 0.2.7 Evaluator with the
# subprocess sandbox, tasks run sequentially under each submission's own eval_config.yaml, like the scorer.
# Outputs: /kaggle/working/run.log, /kaggle/working/results/<name>/ (task_results.jsonl, summary.json, logs/), <name>.tgz
import asyncio, glob, json, os, pathlib, subprocess, sys, time
T0 = time.time()
RUNS = [  # (results name, path inside the repo); later runs are skipped if the session budget would be exceeded
    ("l4-v41-day3", "experiments/variants/v4-1"),
    ("l4-v43-day4", "submission"),
]
SESSION_BUDGET_H = 11.0
EST_RUN_H = 3.4
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None, check=False):
    log("$", cmd[:240]); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
    out = (r.stdout[-2000:] + ("\n" + r.stderr[-2000:] if r.stderr.strip() else "")).strip()
    if out: log(out)
    if check and r.returncode != 0: raise SystemExit(f"command failed rc={r.returncode}: {cmd[:120]}")
    return r
def first(pattern):
    hits = sorted(glob.glob(pattern, recursive=True)); return hits[0] if hits else None

# 0. hardware: this kernel only makes sense on the 4x L4 shape
sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nproc; free -g | head -2; df -h /tmp /kaggle/working | tail -2")
ngpu = int(subprocess.run("nvidia-smi -L | wc -l", shell=True, capture_output=True, text=True).stdout.strip() or 0)
log("GPUs:", ngpu)
if ngpu < 4:
    log("FATAL: fewer than 4 GPUs; not the scorer shape. Stopping."); sys.exit(0)

# 1. inputs
tasks = first("/kaggle/input/**/tasks.jsonl"); assert tasks, "competition data not found"
DATA = pathlib.Path(tasks).parent; log("DATA =", DATA)
whl = first("/kaggle/input/**/swegemma-*.whl"); assert whl, "wheelhouse not found"
WHEELHOUSE = pathlib.Path(whl).parent; log("WHEELHOUSE =", WHEELHOUSE)
cfg = [p for p in glob.glob("/kaggle/input/**/config.json", recursive=True) if "31b" in p.lower() and "w4a16" in p.lower()]
assert cfg, "31B W4A16 model not attached"; MODEL_PATH = str(pathlib.Path(sorted(cfg)[0]).parent); log("MODEL_PATH =", MODEL_PATH)

# 2. environment, as in the Getting Started notebook (cell 1); torch is not in the wheelhouse, vLLM 0.19.1 pins 2.10.0
for k, v in {"LITELLM_LOCAL_MODEL_COST_MAP": "True", "TRANSFORMERS_NO_TF": "1", "VLLM_WORKER_MULTIPROC_METHOD": "spawn",
             "VLLM_MEMORY_PROFILER_ESTIMATE_CUDAGRAPHS": "1", "VLLM_ENGINE_READY_TIMEOUT_S": "1200", "VLLM_NO_USAGE_STATS": "1",
             "OTEL_SDK_DISABLED": "true", "PYTORCH_CUDA_ALLOC_CONF": "expandable_segments:True"}.items():
    os.environ[k] = v
tv = subprocess.run([sys.executable, "-c", "import torch; print(torch.__version__)"], capture_output=True, text=True).stdout.strip()
log("preinstalled torch:", tv)
if not tv.startswith("2.10.0"):
    sh(f"{sys.executable} -m pip install -q torch==2.10.0 torchvision==0.25.0 torchaudio==2.10.0 --index-url https://download.pytorch.org/whl/cu128", timeout=3600, check=True)
for pth in glob.glob("/usr/local/lib/python*/dist-packages/*cutlass*.pth") + glob.glob("/usr/local/lib/python*/site-packages/*cutlass*.pth"):
    try: os.unlink(pth)
    except OSError: pass
tmp = pathlib.Path("/tmp/wheelhouse"); tmp.mkdir(exist_ok=True)
for w in WHEELHOUSE.glob("*.whl"):
    if "cutlass" in w.name.lower(): continue
    name = w.name.replace("cu128", "+cu128") if ("cu128" in w.name and "+" not in w.name) else w.name
    if not (tmp / name).exists(): os.symlink(w, tmp / name)
sh(f"{sys.executable} -m pip install -q --no-deps --force-reinstall {' '.join(sorted(str(w) for w in tmp.glob('*.whl')))}", timeout=3600, check=True)
sh(f"{sys.executable} -c 'import torch, vllm, swegemma, google.adk; print(\"torch\", torch.__version__, \"vllm\", vllm.__version__, \"adk\", google.adk.__version__)'", check=True)

# 3. our submissions
sh("cd /kaggle/working && rm -rf gemma-swe-agent && git clone -q https://github.com/happyc0der/gemma-swe-agent.git && cd gemma-swe-agent && git log --oneline | head -1", check=True)
REPO = pathlib.Path("/kaggle/working/gemma-swe-agent")
splits = json.loads((REPO / "experiments/splits.json").read_text())
HOLDOUT = [t for t in splits["holdout"] if t not in set(splits["env_unstable"])]
log("holdout tasks:", len(HOLDOUT))

# 4. vLLM server, flags from the Getting Started notebook (cell 7)
import litellm, torch, yaml
litellm.drop_params = True
from adk_submission import VllmConfig, VllmServer, discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator
from swegemma.models.discovery import validate_single_declared_model
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
TARGET = "gemma-4-31b-it-qat-w4a16-ct"
first_sub = REPO / RUNS[0][1]
server = VllmServer(VllmConfig(
    model=MODEL_PATH, port=8000, host="127.0.0.1", tool_call_parser="gemma4", reasoning_parser="gemma4",
    default_chat_template_kwargs={"enable_thinking": True}, max_model_len=32768,
    dtype="bfloat16" if torch.cuda.is_bf16_supported() else "auto", gpu_memory_utilization=0.90,
    enable_auto_tool_choice=True, enable_lora=True, max_loras=8, max_lora_rank=128,
    tensor_parallel_size=4, startup_timeout=60 * 20),
    adapter_manifest=discover_adapters(str(first_sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS))
ts = time.time(); server.start(); log(f"vLLM up on {server.base_url} (tp=4) after {time.time()-ts:.0f}s")

# 5. evaluate each submission on the holdout, sequentially, with its own eval_config.yaml
def evaluate(name, rel):
    sub = REPO / rel
    ev = yaml.safe_load((sub / "eval_config.yaml").read_text()); ev = ev.get("evaluation", ev)
    declared = validate_single_declared_model(sub)
    adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    models = server.create_model_registry(aliases=[declared, TARGET], model_prefix="openai/", api_key="EMPTY")
    limits, gen = build_submission_limits()
    turns = ev.get("max_turns", ev.get("max_llm_calls"))
    cfg = EvalConfig(
        tasks_path=pathlib.Path(tasks), snapshots_dir=DATA / "snapshots", results_dir=pathlib.Path(f"/kaggle/working/results/{name}"),
        submission_dir=sub, models=models, sandbox="subprocess",
        timeout_seconds=ev.get("timeout_seconds"), max_time_minutes=ev.get("max_time_minutes"),
        max_tool_calls=ev.get("max_tool_calls"), max_turns=int(turns) if turns is not None else None,
        limits=limits, generation_constraints=gen, adapter_manifest=adapters,
        context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
        events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5),
        graph_dir=str(DATA / "graphs"), embeddings_dir=str(DATA / "embeddings"), wheels_dir=DATA / "wheels",
        task_ids=HOLDOUT, concurrency=1, display_mode="quiet", verbose=False)
    log(f"RUN {name}: {rel} eval={ev} tasks={len(HOLDOUT)}")
    t = time.time(); res = asyncio.run(Evaluator(cfg).run())
    log(f"RUN_DONE {name}: resolved {res.resolved}/{res.total} in {(time.time()-t)/60:.0f} min")
    sh(f"cd /kaggle/working/results && tar -czf /kaggle/working/{name}.tgz {name}")
    return res

for name, rel in RUNS:
    elapsed_h = (time.time() - T0) / 3600
    if elapsed_h + EST_RUN_H > SESSION_BUDGET_H:
        log(f"SKIP {name}: {elapsed_h:.1f} h used, not enough session left"); continue
    try:
        evaluate(name, rel)
    except Exception as e:
        log(f"RUN_FAILED {name}: {type(e).__name__}: {e}")
server.stop() if hasattr(server, "stop") else None
log(f"ALL_DONE after {(time.time()-T0)/3600:.2f} h")
