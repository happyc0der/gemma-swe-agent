# Kaggle T4x2: faithful offline eval of a submission variant with the REAL 31B for prompt iteration.
# - official swegemma Evaluator + harness (wheelhouse), scorer-like sandbox via kaggle/faithful_sandbox.py
# - llama.cpp (official QAT Q4_0 GGUF) with thinking OFF, the way the scorer sends it (chat_template_kwargs)
# - each variant's eval_config.yaml, with max_time_minutes scaled by TIME_SCALE because T4s decode ~3x slower than
#   the scorer's 4x L4 (so agents get a scorer-like number of tool calls); tasks run sequentially like the scorer.
import asyncio, glob, json, os, pathlib, subprocess, sys, threading, time, urllib.request
T0 = time.time()
CFG = {"variants": ["experiments/variants/v49"], "time_scale": 3.0, "n_per_repo": {"fastapi/fastapi": 8, "psf/requests": 4, "Textualize/rich": 4},
       "session_budget_h": 11.0}
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
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
    """Find a wheelhouse file by normalized name prefix (Kaggle may rename uploaded files)."""
    norm = lambda s: s.lower().replace("-", "_")
    c = sorted(p for p in WH.glob("*.whl") if norm(p.name).startswith(norm(prefix)))
    assert c, f"no wheel for {prefix}: {sorted(p.name for p in WH.glob('*.whl'))}"
    return str(c[-1])
sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; python3 --version; free -g | head -2")

# 1. official harness + faithful sandbox
sh("ls " + str(WH) + " | head -60")
sh(f"python3 -m pip install -q {wheel('google_genai')} {wheel('google_adk')} 2>&1 | tail -2", timeout=1800)
sh(f"python3 -m pip install -q --no-deps {wheel('swegemma')} {wheel('adk_submission')} {wheel('adk_eval_core')}", timeout=600)
sh("python3 -c 'import swegemma, adk_submission, google.adk; print(\"harness ok\", google.adk.__version__)'")
sh("python3 -m pip install -q litellm docker networkx cachetools python-dotenv huggingface_hub 2>&1 | tail -2", timeout=1800)
sh("cd /kaggle/working && rm -rf gemma-swe-agent && git clone -q https://github.com/happyc0der/gemma-swe-agent.git && cd gemma-swe-agent && git log --oneline | head -1")
REPO = pathlib.Path("/kaggle/working/gemma-swe-agent"); sys.path.insert(0, str(REPO / "kaggle"))
import logging; logging.basicConfig(level=logging.WARNING)
import faithful_sandbox as fs
log("prepare_host:", json.dumps(fs.prepare_host(DATA))); fs.apply()

# 2. llama.cpp + weights
sh("mkdir -p /tmp/cudalib && d=$(dirname $(find /usr/lib /usr/local -name 'libcuda.so.1' 2>/dev/null | head -1)); ln -sf $d/libcuda.so.1 /tmp/cudalib/libcuda.so")
sh("cd /tmp && git clone -q --depth 1 https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF -DCMAKE_LIBRARY_PATH='/tmp/cudalib;/usr/local/cuda/lib64/stubs' -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc > /dev/null 2>&1; cmake --build build --config Release -j 4 --target llama-server 2>&1 | tail -1", timeout=3600)
os.environ["HF_HOME"] = "/tmp/hf"
from huggingface_hub import hf_hub_download
t = time.time(); gguf = hf_hub_download("google/gemma-4-31B-it-qat-q4_0-gguf", "gemma-4-31B_q4_0-it.gguf", local_dir="/tmp/gguf"); log(f"gguf in {time.time()-t:.0f}s")
helptext = subprocess.run("/tmp/llama.cpp/build/bin/llama-server --help 2>&1", shell=True, capture_output=True, text=True).stdout
SERVER_CMD = ["stdbuf", "-oL", "-eL", "/tmp/llama.cpp/build/bin/llama-server", "-m", gguf, "-ngl", "999", "-sm", "layer", "-c", "32768", "-np", "1",
              "--jinja", "--host", "127.0.0.1", "--port", "8000", "--alias", "gemma-4-31b-it-qat-w4a16-ct", "-fa", "on", "--reasoning-format", "auto", "--threads-http", "8",
              "--cache-ram", "0"]   # the default 8 GB host prompt cache pushed RSS to ~31 of 32 GB and got the server OOM-killed
if "--chat-template-kwargs" in helptext:
    SERVER_CMD += ["--chat-template-kwargs", '{"enable_thinking": false}']   # default; the harness also sends it per request
log("server default thinking off:", "--chat-template-kwargs" in helptext)
def start_server(tag):
    srv = subprocess.Popen(SERVER_CMD, stdout=open(f"/kaggle/working/llama-{tag}.log", "a"), stderr=subprocess.STDOUT, env=os.environ)   # default mmap: with every layer on the GPUs the host copy is reclaimable page cache (dropped each minute)
    for i in range(80):
        time.sleep(15)
        try: urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5).read(); log(f"llama-server up ({tag}) after {(i+1)*15}s"); return srv
        except Exception:
            if srv.poll() is not None: log(f"llama-server died ({tag}):", open(f"/kaggle/working/llama-{tag}.log").read()[-1200:]); return None
    return None
server = start_server("0")
if server is None: sys.exit(1)
def mem():
    return subprocess.run("free -m | sed -n 2p; cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.max 2>/dev/null | tr '\\n' ' '",
                          shell=True, capture_output=True, text=True).stdout.strip()
def watchdog():
    global server; n = 0; k = 0
    while True:
        time.sleep(20); k += 1
        if k % 3 == 0:   # every minute: try to drop page cache (counted against the cgroup) and log memory every 10 min
            subprocess.run("sync; echo 1 > /proc/sys/vm/drop_caches", shell=True, capture_output=True)
            if k % 30 == 0: log("MEM", mem())
        if server.poll() is not None:
            n += 1; log(f"WATCHDOG: llama-server exited rc={server.returncode}; mem: {mem()}; restarting"); server = start_server(str(n))
            if server is None: return
threading.Thread(target=watchdog, daemon=True).start()
# Check that thinking is really off: a tool-free request must come back without reasoning text.
req = json.dumps({"model": "gemma-4-31b-it-qat-w4a16-ct", "max_tokens": 60, "temperature": 0, "chat_template_kwargs": {"enable_thinking": False},
                  "messages": [{"role": "user", "content": "Reply with the single word OK."}]}).encode()
resp = json.loads(urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions", req, {"Content-Type": "application/json"}), timeout=300).read())
m = resp["choices"][0]["message"]; log("thinking check: content=", repr(m.get("content"))[:80], "| reasoning=", repr(m.get("reasoning_content"))[:80], "| usage=", resp.get("usage"))

# 3. evaluate each variant on the subset, sequentially, with its own (time-scaled) eval_config
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
import litellm, yaml
litellm.drop_params = True
from adk_submission import discover_adapters
from swegemma.config import ALLOWED_ADAPTER_EXTENSIONS, EvalConfig, build_submission_limits
from swegemma.evaluate import Evaluator
from swegemma.models.registry import setup_gemma_model_registry
from swegemma.models import load_tasks
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.apps._configs import EventsCompactionConfig
splits = json.loads((REPO / "experiments/splits.json").read_text())
hold = [t for t in splits["holdout"] if t not in set(splits["env_unstable"])]
tasks = {t.instance_id: t for t in load_tasks(pathlib.Path(tasks_file))}
subset, per = [], {}
for iid in hold:
    r = tasks[iid].repo
    if per.get(r, 0) < CFG["n_per_repo"].get(r, 0): subset.append(iid); per[r] = per.get(r, 0) + 1
log("subset", len(subset), per)
for rel in CFG["variants"]:
    if (time.time() - T0) / 3600 > CFG["session_budget_h"] - 3.5: log("SKIP", rel, "(session budget)"); continue
    sub = REPO / rel; name = "faithful-" + pathlib.Path(rel).name
    ev = yaml.safe_load((sub / "eval_config.yaml").read_text()); ev = ev.get("evaluation", ev)
    adapters = discover_adapters(str(sub), adapter_extensions=ALLOWED_ADAPTER_EXTENSIONS)
    models = setup_gemma_model_registry(api_base="http://127.0.0.1:8000/v1", served_model="gemma-4-31b-it-qat-w4a16-ct", adapter_manifest=adapters)
    limits, gen = build_submission_limits()
    cfg = EvalConfig(tasks_path=pathlib.Path(tasks_file), snapshots_dir=DATA / "snapshots", results_dir=pathlib.Path(f"/kaggle/working/results/{name}"),
                     submission_dir=sub, models=models, sandbox="subprocess", timeout_seconds=ev.get("timeout_seconds"),
                     max_time_minutes=float(ev["max_time_minutes"]) * CFG["time_scale"], max_tool_calls=ev.get("max_tool_calls"),
                     max_turns=ev.get("max_turns"), limits=limits, generation_constraints=gen, adapter_manifest=adapters,
                     context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=1800, cache_intervals=10),
                     events_compaction_config=EventsCompactionConfig(compaction_interval=15, overlap_size=2, token_threshold=14336, event_retention_size=5),
                     graph_dir=str(DATA / "graphs"), embeddings_dir=str(DATA / "embeddings"), wheels_dir=DATA / "wheels",
                     task_ids=subset, concurrency=1, display_mode="quiet")
    log(f"RUN {name}: eval={ev} scaled time={cfg.budget.time_minutes} min, {len(subset)} tasks")
    t = time.time(); res = asyncio.run(Evaluator(cfg).run())
    log(f"RUN_DONE {name}: resolved {res.resolved}/{res.total} in {(time.time()-t)/60:.0f} min")
    sh(f"cd /kaggle/working/results && tar -czf /kaggle/working/{name}.tgz {name}")
server.terminate(); log(f"ALL_DONE after {(time.time()-T0)/3600:.2f} h")
