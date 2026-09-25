# Probe: can Kaggle's free GPU serve the competition model (gemma-4-31B-it-qat-w4a16-ct) with vLLM?
# Logs everything to /kaggle/working/probe.log so `kaggle kernels output` can retrieve it.
import subprocess, sys, os, time, json, pathlib, urllib.request, shutil
LOG = open("/kaggle/working/probe.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, **kw):
    log("$", cmd); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, **kw); log(r.stdout[-3000:], r.stderr[-3000:]); return r

log("nvidia-smi:"); sh("nvidia-smi --query-gpu=name,memory.total,compute_cap --format=csv")
sh("df -h /kaggle/working / | tail -2; free -g | head -2; python -V")
log("pip install vllm"); r = sh(f"{sys.executable} -m pip install -q vllm 2>&1 | tail -3")
sh(f"{sys.executable} -c 'import vllm, torch; print(vllm.__version__, torch.__version__, torch.cuda.device_count())'")

MODEL = "google/gemma-4-31B-it-qat-w4a16-ct"
log("download", MODEL)
sh(f"{sys.executable} -m pip install -q huggingface_hub 2>&1 | tail -1")
os.environ["HF_HOME"] = "/tmp/hf"  # /kaggle/working is only 20 GB; the root overlay has >1 TB free
from huggingface_hub import snapshot_download
t = time.time(); path = snapshot_download(MODEL, local_dir="/tmp/model"); log("downloaded to", path, f"in {time.time()-t:.0f}s"); sh("du -sh /tmp/model; df -h /tmp | tail -1")

ATTEMPTS = [
    ("eager-16k", ["--enforce-eager", "--max-model-len", "16384", "--max-num-seqs", "1", "--gpu-memory-utilization", "0.95"]),
    ("flex-eager-16k", ["--attention-backend", "FLEX_ATTENTION", "--enforce-eager", "--max-model-len", "16384", "--max-num-seqs", "1", "--gpu-memory-utilization", "0.95"]),
    ("eager-8k", ["--enforce-eager", "--max-model-len", "8192", "--max-num-seqs", "1", "--gpu-memory-utilization", "0.95"]),
]
up = False; server = None
for name, extra in ATTEMPTS:
    log("start vLLM TP=2 attempt:", name)
    server = subprocess.Popen([sys.executable, "-m", "vllm.entrypoints.openai.api_server", "--model", "/tmp/model",
        "--served-model-name", "gemma-4-31b-it-qat-w4a16-ct", "--tensor-parallel-size", "2",
        "--dtype", "half", "--limit-mm-per-prompt", '{"image":0,"audio":0}',
        "--tool-call-parser", "gemma4", "--enable-auto-tool-choice", "--reasoning-parser", "gemma4", "--port", "8000", *extra],
        stdout=open(f"/kaggle/working/vllm-{name}.log", "w"), stderr=subprocess.STDOUT, env={**os.environ, "VLLM_USE_FLASHINFER_SAMPLER": "0"})
    for i in range(80):
        time.sleep(15)
        try:
            urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5).read(); up = True; log(f"vLLM up ({name}) after {(i+1)*15}s"); break
        except Exception:
            if server.poll() is not None:
                tail = open(f"/kaggle/working/vllm-{name}.log").read()
                import re as _re
                err = [l for l in tail.splitlines() if _re.search(r"Error|error:|not supported|out of resource", l)][-3:]
                log(f"vLLM died ({name}):", " | ".join(x[-160:] for x in err)); break
    if up: break
    subprocess.run("pkill -f vllm.entrypoints; sleep 5", shell=True)
if not up:
    log("PROBE_RESULT: vllm_failed"); sys.exit(0)

def call(body):
    t = time.time(); req = urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=900).read()); return d, time.time() - t
tools = [{"type": "function", "function": {"name": "read_file", "description": "Reads a file", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["filepath"]}}}]
d, dt = call({"model": "gemma-4-31b-it-qat-w4a16-ct", "messages": [{"role": "user", "content": "Read src/app.py lines 1 to 20."}], "tools": tools, "max_tokens": 200})
log("tool call:", d["choices"][0]["message"].get("tool_calls"), f"{dt:.1f}s")
d, dt = call({"model": "gemma-4-31b-it-qat-w4a16-ct", "messages": [{"role": "user", "content": "Write 300 words on B-trees."}], "max_tokens": 500})
log(f"speed: {d['usage']['completion_tokens']} tokens in {dt:.1f}s = {d['usage']['completion_tokens']/dt:.1f} tok/s")
d, dt = call({"model": "gemma-4-31b-it-qat-w4a16-ct", "messages": [{"role": "user", "content": "What is 17*23? Think it through."}], "max_tokens": 400, "reasoning_effort": "high"})
log("thinking:", (d["usage"].get("completion_tokens_details") or {}).get("reasoning_tokens"), "reasoning tokens")
log("PROBE_RESULT: ok")
server.terminate()
