# %% [markdown]
# # swelite eval of the real 31B W4A16 model on Kaggle (T4 x2, 32 GB)
# Notebook-as-script. Cells are separated by `# %%`. Accelerator: GPU T4 x2. Internet: ON.
# Secrets: HF_TOKEN (Gemma license accepted on Hugging Face).
#
# Path A (preferred): vLLM serving `google/gemma-4-31B-it-qat-w4a16-ct` with TP=2.
#   T4 is SM 7.5; compressed-tensors W4A16 kernels may refuse. If so, use Path B.
# Path B: llama.cpp server with the official Q4_0 GGUF split over both GPUs.
#   Tool calling through llama.cpp's OpenAI-compatible endpoint + Gemma 4 chat template.
# Both paths expose an OpenAI-compatible /v1 on port 8000, which swelite talks to via LiteLlm.

# %%
import os, subprocess, sys, json, time, pathlib
REPO = "https://github.com/happyc0der/gemma-swe-agent.git"
subprocess.run(["git", "clone", "-q", REPO, "/kaggle/working/gemma-swe-agent"], check=False)
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-e", "/kaggle/working/gemma-swe-agent/harness"], check=True)

# Competition data is attached as an input dataset (add "gemma-4-developer-agent" competition data to the notebook).
DATA = "/kaggle/input/gemma-4-developer-agent"
assert pathlib.Path(DATA, "tasks.jsonl").exists(), "attach the competition dataset"

# %%
# Path A: vLLM
from kaggle_secrets import UserSecretsClient
os.environ["HF_TOKEN"] = UserSecretsClient().get_secret("HF_TOKEN")
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "vllm"], check=True)
MODEL = "google/gemma-4-31B-it-qat-w4a16-ct"
SUB = "/kaggle/working/gemma-swe-agent/submission"
lora_args = []
ad = pathlib.Path(SUB, "adapters")
if ad.is_dir():
    mods = [f"{d.name}={d}" for d in ad.iterdir() if (d / "adapter_config.json").exists()]
    if mods:
        lora_args = ["--enable-lora", "--max-loras", "8", "--max-lora-rank", "128", "--lora-modules", *mods]
server = subprocess.Popen([
    sys.executable, "-m", "vllm.entrypoints.openai.api_server",
    "--model", MODEL, "--served-model-name", "gemma-4-31b-it-qat-w4a16-ct",
    "--tensor-parallel-size", "2", "--gpu-memory-utilization", "0.90",
    "--max-model-len", "32768", "--dtype", "half",  # T4 has no bf16
    "--tool-call-parser", "gemma4", "--enable-auto-tool-choice", "--reasoning-parser", "gemma4",
    "--port", "8000", *lora_args,
], stdout=open("/kaggle/working/vllm.log", "w"), stderr=subprocess.STDOUT)
for _ in range(240):
    time.sleep(10)
    try:
        import urllib.request
        urllib.request.urlopen("http://127.0.0.1:8000/v1/models").read()
        print("vLLM up"); break
    except Exception:
        if server.poll() is not None:
            print(open("/kaggle/working/vllm.log").read()[-3000:]); raise SystemExit("vLLM died; try Path B")

# %%
# Run the fixed 40-task holdout with the subprocess sandbox (no Docker on Kaggle).
splits = json.load(open("/kaggle/working/gemma-swe-agent/experiments/splits.json"))
ids = splits["holdout"]
cmd = ["swelite", "eval", "--data-dir", DATA, "--submission-dir", SUB, "--results-dir", "/kaggle/working/results/holdout",
       "--sandbox", "subprocess", "--concurrency", "4", "--api-base", "http://127.0.0.1:8000/v1"]
for i in ids:
    cmd += ["--task-id", i]
subprocess.run(cmd, check=False)
print(open("/kaggle/working/results/holdout/summary.json").read())

# %%
# Path B (fallback): llama.cpp with the official Q4_0 GGUF.
# subprocess.run(["pip","install","-q","huggingface_hub"]); from huggingface_hub import snapshot_download
# p = snapshot_download("google/gemma-4-31B-it-qat-q4_0-gguf")
# build llama.cpp with CUDA, then: llama-server -m <gguf> -ngl 999 -ts 1,1 -c 32768 --jinja --port 8000 --alias gemma-4-31b-it-qat-w4a16-ct
