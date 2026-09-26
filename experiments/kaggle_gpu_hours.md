# Kaggle GPU hours ledger (account `dankaxon`)

Kaggle's free tier gives about 30 GPU hours per week (T4x2 counts as one session). The CLI cannot read the
remaining quota; the authoritative number is on the Kaggle profile page ("GPU quota"). Hours below are
push-to-finish wall time from this project's logs, so they slightly overstate use when a kernel waited in a queue.
The account also runs other projects' kernels (biohub-*, electric-car), which draw on the same quota.

## Policy
- Evaluation compute is Kaggle (decision 2026-09-26); the MSI laptop is a demo workbench only.
- A GPU run must be able to change a decision: validate a config the proxy cannot separate, calibrate the
  proxy against a Kaggle LB score, or gate LoRA. No exploratory sweeps on GPU hours.
- A full 33-task holdout run of the real 31B on T4x2 costs about 3.5-4 h (sequential, time-bound tasks).
  At ~30 h/week that is at most ~6 runs, so keep at most one queued at a time and keep ~6 h in reserve.
- Log every push here with its purpose; fill in the hours when it finishes.

## Week of 2026-09-25

| kernel / version | accelerator | start (UTC) | end (UTC) | hours | purpose / outcome |
|---|---|---|---|---|---|
| gemma4-31b-vllm-probe v1-v5 | T4x2 | 09-25 14:04 | ~15:50 | ~1.7 | vLLM W4A16 on Turing: all 5 failed |
| gemma4-31b-llamacpp-probe v1-v2 | T4x2 | 09-25 14:44 | ~15:30 | ~0.7 | llama.cpp Q4_0 works |
| gemma4-31b-holdout-eval v1 | T4x2 | 09-25 15:32 | ~15:58 | ~0.4 | setup failure |
| gemma4-31b-holdout-eval v2 | T4x2 | 09-25 15:58 | 16:38 | 0.7 | setup iteration |
| gemma4-31b-holdout-eval v3 | T4x2 | 09-25 16:40 | 17:31 | 0.9 | setup iteration |
| gemma4-31b-holdout-eval v4 | T4x2 | 09-25 17:33 | 18:33 | 1.0 | setup iteration |
| gemma4-31b-holdout-eval v5 | T4x2 | 09-25 18:37 | 20:28 | 1.9 | first partial holdout (1/33, OOM kills) |
| gemma4-31b-holdout-eval v6 | T4x2 | 09-25 20:30 | 21:01 | 0.5 | error (mmap flag) |
| gemma4-31b-holdout-eval v7 | T4x2 | 09-25 21:03 | 09-26 01:18 | 4.3 | error after long run (server SIGKILL) |
| gemma4-31b-holdout-eval v8 | T4x2 | 09-26 01:22 | 05:10 | 3.8 | day-3 config: 3/33 |
| gemma4-31b-holdout-eval v9 | T4x2 | 09-26 05:24 | 09:26 | 4.0 | v4.2: 2/33 |
| gemma4-official-l4-eval v1 | T4x2 (L4 unavailable) | 09-26 16:23 | 16:26 | 0.05 | L4x4 not granted; exited at GPU check |
| gemma4-31b-holdout-eval v10 | T4x2 | 09-26 16:29 (queued) | | | day-4 config (v4.3, 4.5 min): calibrate T4 proxy against the day-4 LB score |
| **total so far** | | | | **~19.9** | |

Setup iterations (v1-v7) cost ~9.7 h; that one-off cost is now paid, and each further holdout run is ~4 h.
