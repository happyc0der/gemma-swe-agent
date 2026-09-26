# Scorer replica on a 16 GB laptop GPU

The scorer's exact inference stack (wheelhouse vLLM 0.19.1, transformers 5.13.1, compressed-tensors 0.15.0.1)
serving the real `gemma-4-31B-it-qat-w4a16-ct` on the MSI's RTX 3080 Ti Laptop (16 GB, PCIe Gen4 x8, WSL2),
driven by the wheelhouse google-adk 1.36.1 / swegemma 0.2.7. Used for fidelity probes, not for bulk evaluation.

## Why it is slow, and how far it could be pushed
Weights (19.5 GB loaded, 18.5 GB with `--language-model-only`) plus the 32k KV cache (4.9 GiB) exceed 16 GB,
so part of the model lives in system RAM and crosses PCIe for every generated token. Decode speed is therefore
set by bytes offloaded divided by host-to-GPU bandwidth. Measured on the laptop:

| host-to-GPU copy under WSL | GiB/s |
|---|---|
| pageable (vLLM's default under WSL) | 7.8 |
| pinned | 11.5 |

Trials, 128-token decode at 32k max context (`v019_trials.log`, `v019_bench.sh`):

| config | offloaded | tok/s |
|---|---|---|
| A: pageable functional-call offload, eager (first version) | 11.5 GiB | 0.38 |
| B: pinned + zero-copy UVA, vision tower skipped, eager | 10.6 GiB | 0.71 |
| H: B + CUDA graphs (needs more offload) | 11.3 GiB | 0.74 |
| P1: prefetch backend, 2 of every 3 layers, eager | 40 layers | 1.09 |
| P2: P1 + CUDA graphs | 40 layers | 1.11 |
| **P3: prefetch, 3 of every 5 layers, CUDA graphs (default)** | **36 layers** | **1.25** |

Dead ends: fp8 KV cache (e4m3 unsupported by Triton on sm86; e5m2 rejected for this checkpoint), 16k context
with half the layers offloaded (KV short by 0.5 GiB). The remaining ceiling is the x8 link: the 31B cannot go
much past ~1.3 tok/s in vLLM on this GPU. llama.cpp with CPU-resident layers would read those layers from DDR5
instead of PCIe and should be several times faster, but it is not the scorer's stack.

## Files
- `apply_vllm_patches.py`: the three local vLLM patches (pinned memory under WSL, offload re-init guard,
  prefetch sizing for packed int32 weights).
- `v019_serve_31b.sh`: server on port 8001; env knobs `OFFLOAD_BACKEND`, `GROUP`, `GROUP_N`, `PREFETCH`,
  `EAGER`, `MAX_LEN`, `KV_DTYPE`, `PIN`. Needs an `nvcc` on PATH for CUDA graphs (borrowed from the vLLM 0.30 venv).
- `v019_switch.sh`: stops other servers, starts the replica, stays alive (launch via Task Scheduler).
- `v019_bench.sh`, `v019_trial.sh`: decode benchmark and one-trial runner.
- `v019_probe.py`: ADK 1.36.1 tool-call probe (thinking off / low / on).
