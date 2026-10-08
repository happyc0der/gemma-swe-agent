# LoRA feasibility gate: QLoRA of gemma-4-31B on Kaggle T4x2 (kernel `dankaxon/gemma4-lora-gate` v1-v4)

Setup: `google/gemma-4-31B-it-qat-q4_0-unquantized` (62.6 GB, public, downloads in ~4.5 min), bitsandbytes nf4 with
fp16 compute, LoRA r=16 on q/k/v/o/gate/up/down of the language model (122M trainable params), gradient
checkpointing, PagedAdamW8bit, loss on the last 1,024 positions via `logits_to_keep` with chunked fp32 CE.
transformers 5.19.0, peft 0.21.2, torch 2.11.

| version | change | outcome |
|---|---|---|
| v1 | 13/13 GiB caps, fp32 AdamW, unchunked loss | model loads (10.2 / 6.8 GiB); 2k step OOM on GPU 0 |
| v2 | 8/13 GiB caps, chunked loss | one 2k step in 36 s, then OOM on fp32 optimizer states |
| v3 | 9/9 GiB caps, 8-bit optimizer | model does not fit in 18 GiB (load error, no training) |
| v4 | 9.5/10 GiB caps | **2,048 tokens: 33-34 s/step, peak 11.6/11.9 GiB; 3,072: 60 s/step, peak 11.8/13.1; 4,096: OOM** |

Adapter names (`base_model.model.model.language_model.layers.N.<proj>.lora_A.weight`) map onto vLLM 0.19.1's Gemma 4
model: its LoRA loader strips `base_model.model.` and applies `hf_to_vllm_mapper` (`model.language_model.` ->
`language_model.model.`); q/k/v and gate/up are packed (`qkv_proj`, `gate_up_proj`) and supported. Runtime behaviour on
the scorer's W4A16 weights cannot be tested on T4 (no vLLM INT4 kernels for Turing).

Verdict: **not viable on T4x2.** The 31B's own successful trajectories are 7k-17k tokens; the ceiling is 3k tokens,
so training would only see fragments without the system prompt and issue, at ~50 tokens/s (~5.5 GPU h per 1M
tokens). The same recipe would fit on the 4x L4 notebook shape (96 GB), which organizers say exists for
participants but which the CLI does not grant this account. ~0.8 GPU h spent on v1-v4.
