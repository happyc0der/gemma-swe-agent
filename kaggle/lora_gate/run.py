# Kaggle T4x2 feasibility gate for LoRA on gemma-4-31B (QAT unquantized weights, loaded in 4-bit).
# Answers, before any data generation: does QLoRA training of the 31B fit on two 15 GB T4s, at what sequence
# length, how fast, and what adapter module names come out (they must match vLLM's Gemma 4 LoRA targets).
# Random token ids: memory and time do not depend on the content. Loss only on the last LABEL_TOKENS positions
# (agent turns are a small share of a trajectory), computed via logits_to_keep so full-vocab logits never exist.
import json, os, subprocess, sys, time, traceback
T0 = time.time(); BUDGET_S = 80 * 60
LOG = open("/kaggle/working/run.log", "a", buffering=1)
def log(*a):
    s = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a); print(s, flush=True); LOG.write(s + "\n")
def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True); log("$", cmd[:160]); log((r.stdout + r.stderr)[-1500:].strip()); return r
RESULT = {"steps": []}
def save():
    json.dump(RESULT, open("/kaggle/working/result.json", "w"), indent=1)

sh("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader; free -g | head -2; df -h /tmp | tail -1; python3 --version")
sh("python3 -m pip install -q -U 'transformers>=4.57' peft bitsandbytes accelerate hf_transfer 2>&1 | tail -3")
import torch, transformers, peft
log("versions: torch", torch.__version__, "transformers", transformers.__version__, "peft", peft.__version__)
RESULT["versions"] = {"torch": torch.__version__, "transformers": transformers.__version__, "peft": peft.__version__}

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
from huggingface_hub import snapshot_download
t = time.time()
ckpt = snapshot_download("google/gemma-4-31B-it-qat-q4_0-unquantized", local_dir="/tmp/ckpt",
                         allow_patterns=["*.json", "*.safetensors", "*.jinja", "tokenizer*"])
RESULT["download_s"] = round(time.time() - t); log(f"download {RESULT['download_s']} s"); sh("du -sh /tmp/ckpt; df -h /tmp | tail -1")

from transformers import AutoModelForCausalLM, BitsAndBytesConfig
bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16,
                         bnb_4bit_use_double_quant=True)
t = time.time()
try:
    model = AutoModelForCausalLM.from_pretrained(ckpt, quantization_config=bnb, device_map="auto", torch_dtype=torch.float16,
                                                 max_memory={0: "9500MiB", 1: "10GiB", "cpu": "24GiB"}, low_cpu_mem_usage=True)
except Exception:
    log("AutoModelForCausalLM failed:\n" + traceback.format_exc()[-2000:])
    from transformers import AutoModelForImageTextToText
    model = AutoModelForImageTextToText.from_pretrained(ckpt, quantization_config=bnb, device_map="auto", torch_dtype=torch.float16,
                                                        max_memory={0: "9500MiB", 1: "10GiB", "cpu": "24GiB"}, low_cpu_mem_usage=True)
RESULT["load_s"] = round(time.time() - t); RESULT["model_class"] = type(model).__name__
devmap = getattr(model, "hf_device_map", {}); RESULT["devices"] = sorted({str(v) for v in devmap.values()})
log("loaded", type(model).__name__, f"in {RESULT['load_s']} s; devices", RESULT["devices"])
for i in range(torch.cuda.device_count()):
    log(f"gpu{i} allocated after load: {torch.cuda.memory_allocated(i) / 2**30:.2f} GiB")
log("device map sample:", {k: v for k, v in list(devmap.items())[:4] + list(devmap.items())[-4:]})
RESULT["mem_after_load_gib"] = [round(torch.cuda.memory_allocated(i) / 2**30, 2) for i in range(torch.cuda.device_count())]
save()
if "cpu" in RESULT["devices"] or "disk" in RESULT["devices"]:
    log("GATE: model does not fit on the two GPUs (layers offloaded); stopping"); RESULT["verdict"] = "does not fit"; save(); sys.exit(0)

from peft import LoraConfig, get_peft_model
# not prepare_model_for_kbit_training: it upcasts every non-quantized weight to fp32 (the 1.4B-param embedding alone ~5.6 GB)
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
model.enable_input_require_grads()
targets = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
cfg = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.0, target_modules=targets, task_type="CAUSAL_LM",
                 exclude_modules=r".*(vision|audio|multi_modal).*")
model = get_peft_model(model, cfg)
trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
RESULT["trainable_params"] = trainable; log("trainable params", trainable)
names = [n for n, _ in model.named_parameters() if "lora_A" in n][:4]; RESULT["lora_param_names_sample"] = names; log("lora names", names)
import bitsandbytes as bnb_lib
opt = bnb_lib.optim.PagedAdamW8bit([p for p in model.parameters() if p.requires_grad], lr=1e-4)   # fp32 AdamW states (~1 GB) OOMed in v2
first_dev = next(model.parameters()).device
vocab = model.config.get_text_config().vocab_size if hasattr(model.config, "get_text_config") else model.config.vocab_size
LABEL_TOKENS = 1024
model.train()
for seq in (2048, 3072, 4096, 6144, 8192, 12288):
    if time.time() - T0 > BUDGET_S - 600: log("budget: skipping", seq); break
    for i in range(torch.cuda.device_count()): torch.cuda.reset_peak_memory_stats(i)
    ids = torch.randint(10, vocab - 10, (1, seq), device="cuda:0")
    rec = {"seq": seq}
    try:
        for step in range(2):
            torch.cuda.synchronize(); t = time.time()
            out = model(input_ids=ids, logits_to_keep=LABEL_TOKENS + 1, use_cache=False)
            logits = out.logits[0, :-1]                       # fp16 [LABEL_TOKENS, vocab]; no fp32 copy of the whole block
            labels = ids[0, -LABEL_TOKENS:].to(logits.device)
            loss = sum(torch.nn.functional.cross_entropy(logits[i:i + 128].float(), labels[i:i + 128], reduction="sum")
                       for i in range(0, LABEL_TOKENS, 128)) / LABEL_TOKENS
            loss.backward(); opt.step(); opt.zero_grad(set_to_none=True)
            del out, logits
            torch.cuda.synchronize(); rec[f"step{step}_s"] = round(time.time() - t, 1)
        rec["loss"] = round(float(loss), 3)
        rec["peak_gib"] = [round(torch.cuda.max_memory_allocated(i) / 2**30, 2) for i in range(torch.cuda.device_count())]
        rec["ok"] = True
    except torch.cuda.OutOfMemoryError as e:
        rec["ok"] = False; rec["error"] = "OOM: " + str(e)[:200]; opt.zero_grad(set_to_none=True); torch.cuda.empty_cache()
    except Exception as e:
        rec["ok"] = False; rec["error"] = traceback.format_exc()[-800:]
    log("STEP", json.dumps(rec)); RESULT["steps"].append(rec); save()
    if not rec["ok"]: break

model.save_pretrained("/kaggle/working/adapter_probe")
sh("ls -la /kaggle/working/adapter_probe; cat /kaggle/working/adapter_probe/adapter_config.json | head -40")
from safetensors import safe_open
with safe_open("/kaggle/working/adapter_probe/adapter_model.safetensors", "pt") as f:
    keys = list(f.keys())
RESULT["adapter_keys_sample"] = keys[:6]; RESULT["adapter_keys"] = len(keys)
ok = [r for r in RESULT["steps"] if r.get("ok")]
RESULT["verdict"] = f"fits up to {ok[-1]['seq']} tokens" if ok else "no training step fit"
log("GATE VERDICT:", RESULT["verdict"], f"after {(time.time() - T0) / 60:.0f} min"); save()
