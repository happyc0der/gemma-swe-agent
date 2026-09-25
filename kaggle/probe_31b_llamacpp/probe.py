# Probe B: llama.cpp with the official Gemma 4 31B QAT Q4_0 GGUF split across Kaggle's two T4s. Logs to /kaggle/working/probe.log.
import subprocess, sys, os, time, json, urllib.request
LOG = open("/kaggle/working/probe.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd, timeout=None):
    log("$", cmd); r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout); log(r.stdout[-2500:], r.stderr[-2500:]); return r
sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; nvcc --version | tail -1; cmake --version | head -1")
log("build llama.cpp (CUDA)")
sh("cd /tmp && git clone -q --depth 1 https://github.com/ggml-org/llama.cpp && cd llama.cpp && cmake -B build -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=75 -DLLAMA_CURL=OFF > /dev/null && cmake --build build --config Release -j 4 --target llama-server 2>&1 | tail -3", timeout=3600)
sh("ls -la /tmp/llama.cpp/build/bin/llama-server")
os.environ["HF_HOME"] = "/tmp/hf"
sh(f"{sys.executable} -m pip install -q huggingface_hub 2>&1 | tail -1")
from huggingface_hub import snapshot_download, list_repo_files
REPO = "google/gemma-4-31B-it-qat-q4_0-gguf"
files = list_repo_files(REPO); log("repo files:", files)
t = time.time(); path = snapshot_download(REPO, local_dir="/tmp/gguf"); log(f"downloaded in {time.time()-t:.0f}s"); sh("ls -la /tmp/gguf; df -h /tmp | tail -1")
gguf = [f for f in os.listdir("/tmp/gguf") if f.endswith(".gguf")]
main = sorted(gguf, key=len)[0]; log("using", main)
log("start llama-server across 2 GPUs")
server = subprocess.Popen(["/tmp/llama.cpp/build/bin/llama-server", "-m", f"/tmp/gguf/{main}", "-ngl", "999", "-sm", "layer", "-c", "32768", "-np", "2", "--jinja",
    "--host", "127.0.0.1", "--port", "8000", "--alias", "gemma-4-31b-it-qat-w4a16-ct", "-fa", "on"], stdout=open("/kaggle/working/llama.log", "w"), stderr=subprocess.STDOUT)
up = False
for i in range(80):
    time.sleep(15)
    try:
        urllib.request.urlopen("http://127.0.0.1:8000/v1/models", timeout=5).read(); up = True; log(f"llama-server up after {(i+1)*15}s"); break
    except Exception:
        if server.poll() is not None:
            log("llama-server died; tail:", open("/kaggle/working/llama.log").read()[-3000:]); break
if not up: log("PROBE_RESULT: llama_failed"); sys.exit(0)
def call(body):
    t = time.time(); req = urllib.request.Request("http://127.0.0.1:8000/v1/chat/completions", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=900).read()); return d, time.time() - t
tools = [{"type": "function", "function": {"name": "read_file", "description": "Reads a file", "parameters": {"type": "object", "properties": {"filepath": {"type": "string"}, "start_line": {"type": "integer"}, "end_line": {"type": "integer"}}, "required": ["filepath"]}}}]
d, dt = call({"model": "gemma-4-31b-it-qat-w4a16-ct", "messages": [{"role": "user", "content": "Read src/app.py lines 1 to 20."}], "tools": tools, "max_tokens": 200})
m = d["choices"][0]["message"]; log("tool call:", m.get("tool_calls"), "| content:", (m.get("content") or "")[:120], f"{dt:.1f}s")
d, dt = call({"model": "gemma-4-31b-it-qat-w4a16-ct", "messages": [{"role": "user", "content": "Write 300 words on B-trees."}], "max_tokens": 500})
log(f"speed: {d['usage']['completion_tokens']} tokens in {dt:.1f}s = {d['usage']['completion_tokens']/dt:.1f} tok/s")
log("PROBE_RESULT: ok"); server.terminate()
