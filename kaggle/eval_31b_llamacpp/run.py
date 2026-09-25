# Kaggle T4x2: evaluate a submission config with the REAL 31B (official QAT Q4_0 GGUF via llama.cpp) using swelite's subprocess sandbox.
# Inputs: competition data attached at /kaggle/input/gemma-4-developer-agent. Outputs: /kaggle/working/results/<name>/ and run.log.
import subprocess, sys, os, time, json, urllib.request, pathlib
CFG = {"submission": "submission", "results": "k31b-day3cfg", "max_min": 5.5, "max_calls": 30, "split": "holdout", "limit": 33, "concurrency": 2, "extra": []}
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None):
    log("$", cmd[:200]); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout); log(r.stdout[-1500:], r.stderr[-1500:]); return r
DATA = "/kaggle/input/gemma-4-developer-agent"; assert pathlib.Path(DATA, "tasks.jsonl").exists(), "attach the competition dataset"
sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; df -h /tmp | tail -1")
# 1. harness
sh("cd /kaggle/working && git clone -q https://github.com/happyc0der/gemma-swe-agent.git && cd gemma-swe-agent && git log --oneline | head -1")
sh(f"{sys.executable} -m pip install -q -e /kaggle/working/gemma-swe-agent/harness 2>&1 | grep -viE 'warning|incompatible' | tail -2")
sh(f"{sys.executable} -c 'import google.adk, swelite; print(\"adk\", google.adk.__version__)'")
# 2. llama.cpp
sh("mkdir -p /tmp/cudalib && d=$(dirname $(find /usr/lib /usr/local -name 'libcuda.so.1' 2>/dev/null | head -1)); ln -sf $d/libcuda.so.1 /tmp/cudalib/libcuda.so")
sh("cd /tmp && git clone -q --depth 1 https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF -DCMAKE_LIBRARY_PATH='/tmp/cudalib;/usr/local/cuda/lib64/stubs' -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc > /dev/null 2>&1; cmake --build build --config Release -j 4 --target llama-server 2>&1 | tail -1", timeout=3600)
# 3. weights
os.environ["HF_HOME"] = "/tmp/hf"; sh(f"{sys.executable} -m pip install -q huggingface_hub 2>&1 | tail -1")
from huggingface_hub import hf_hub_download
t = time.time(); gguf = hf_hub_download("google/gemma-4-31B-it-qat-q4_0-gguf", "gemma-4-31B_q4_0-it.gguf", local_dir="/tmp/gguf"); log(f"gguf in {time.time()-t:.0f}s")
# 4. serve (OpenAI-compatible, tool calls via --jinja, 2 parallel slots, 32k context each)
server = subprocess.Popen(["/tmp/llama.cpp/build/bin/llama-server", "-m", gguf, "-ngl", "999", "-sm", "layer", "-c", str(32768 * CFG["concurrency"]), "-np", str(CFG["concurrency"]), "--jinja",
    "--host", "127.0.0.1", "--port", "8000", "--alias", "gemma-4-31b-it-qat-w4a16-ct", "-fa", "on", "--reasoning-format", "auto"], stdout=open("/kaggle/working/llama.log", "w"), stderr=subprocess.STDOUT)
for i in range(80):
    time.sleep(15)
    try: urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5).read(); log(f"llama-server up after {(i+1)*15}s"); break
    except Exception:
        if server.poll() is not None: log("llama-server died:", open("/kaggle/working/llama.log").read()[-2000:]); sys.exit(1)
# 5. evaluate
splits = json.load(open("/kaggle/working/gemma-swe-agent/experiments/splits.json"))
ids = [i for i in splits[CFG["split"]] if i not in splits["env_unstable"]][: CFG["limit"]]
cmd = ["swelite", "eval", "--data-dir", DATA, "--submission-dir", f"/kaggle/working/gemma-swe-agent/{CFG['submission']}", "--results-dir", f"/kaggle/working/results/{CFG['results']}",
       "--sandbox", "subprocess", "--concurrency", str(CFG["concurrency"]), "--api-base", "http://127.0.0.1:8000/v1", "--served-model", "gemma-4-31b-it-qat-w4a16-ct",
       "--max-time-minutes", str(CFG["max_min"]), "--max-tool-calls", str(CFG["max_calls"]), *CFG["extra"]]
for i in ids: cmd += ["--task-id", i]
log("eval:", " ".join(cmd[:14]), f"... {len(ids)} tasks")
t = time.time(); r = subprocess.run(cmd, capture_output=True, text=True); log(r.stdout[-4000:], r.stderr[-2000:]); log(f"eval took {(time.time()-t)/60:.0f} min")
try: log("SUMMARY", open(f"/kaggle/working/results/{CFG['results']}/summary.json").read())
except Exception as e: log("no summary", e)
sh(f"cd /kaggle/working/results && tar -czf /kaggle/working/{CFG['results']}.tgz {CFG['results']} --exclude='*/test_outputs/*' && ls -la /kaggle/working/*.tgz")
server.terminate(); log("RUN_DONE")
