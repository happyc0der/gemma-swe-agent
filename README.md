# gemma-swe-agent

Solo entry for the Kaggle **Google - The Gemma 4 Developer Agent Competition** (Sep 23 - Dec 2, 2026): post-train and scaffold `gemma-4-31b-it-qat-w4a16-ct` into an autonomous software-engineering agent that fixes real GitHub issues offline on 4x L4 GPUs.

See `docs/competition.md` for the competition digest, `docs/HARNESS_README.md` for the organizers' harness spec, and `experiments/` for every run.

## Results so far

| date | where | config | result |
|---|---|---|---|
| 09-24 | Kaggle (31B, 4x L4, ~60 hidden tasks) | organizers' sample prompt, 8 min / 40 calls | **0.00** |
| 09-24 | harness self-check (Mac amd64 + MSI native) | gold patches / no patch, 129 public tasks | 109/129 pass, 0 (2) pass unfixed |
| 09-25 | MSI proxy (12B W4A16, vLLM), 33 holdout | prompt v3, temp 0.2, 10 min / 50 calls | 6/33 |
| 09-25 | MSI proxy | prompt v3, temp 0.7 | 6/33 (loops fixed, overflow up) |
| 09-25 | MSI proxy | prompt v4 (context-budget rules), temp 0.7, 2048 cap | **7/33** |
| 09-25 | MSI proxy | day-3 config: v4, 5.5 min / 30 calls | 5/33 (24 explicit submits, overflow 12 -> 2) |
| 09-25 | MSI proxy | v4 with thinking on (thoughts kept in history) | 7/33 (loops gone, overflow up); union of all runs 10/33 |
| 09-25 | MSI proxy | day-3 config with thinking on | 7/33 holdout, 15/74 dev |
| 09-25 | **Kaggle T4x2, real 31B** (llama.cpp Q4_0) | day-3 config | 1/33 while the server was OOM-killed 11 times; pipeline proven end to end on the competition model |
| 09-25 | Kaggle | prompt v3, temp 0.2, thinking 2048, 10 min / 50 calls | **0.00** |
| 09-26 | Kaggle | prompt v4.1 (write_file warning), temp 0.7, thinking off, 5.5 min / 30 calls | scoring at 05:30 UTC |
| 09-26 | **Kaggle T4x2, real 31B** (llama.cpp Q4_0, page cache fixed) | day-3 config | **3/33**, 192 min, one server restart |
| 09-26 | MSI proxy, **official `swegemma` harness** (wheelhouse) | prompt v4.1 | 0/2 before it was stopped: 20 of 24 `read_file` calls rejected (string line numbers) |
| 09-26 | MSI proxy, official harness | prompt v4.2 (string-only tool arguments, `sed -n` ranges), then v4.1, sample-noadapter, v4.2+analyzer | running |

Key findings: the organizers released the real harness on 09-25 (`harness/official/`, from the Kaggle wheelhouse dataset) and running our submission through it exposed the bug behind three 0.00 scores: the pinned vLLM's Gemma 4 tool-call parser keeps quoted values as strings and nothing coerces them, so every `read_file` with a line range, and any boolean or numeric option, fails on the scorer while our re-implementation (newer ADK and vLLM) silently returned integers. Prompt v4.2 uses string-only tool arguments. Also: the competition's 31B runs on Kaggle's free T4 pair only through llama.cpp (vLLM's INT4 kernels need Ampere); ADK never compacts context inside a task, so trajectories die at the 32k window after ~20 full-size tool outputs; low temperature causes verbatim retry loops; the Ollama proxy ignores `max_tokens` and has no thinking budget, so vLLM is the only faithful local proxy.

## Layout
- `submission/` - exactly what gets zipped and uploaded (YAML agent config, prompts, skills, adapters).
- `harness/` - `swelite`, a local re-implementation of the `swegemma` evaluator written before it was released (Docker/subprocess sandboxes, the 9 tools, ADK compile, verification, failure taxonomy), and `harness/official/`, the organizers' released source (swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0) used for all config checks since 09-26; `docs/harness-fidelity.md` lists every difference.
- `experiments/` - one folder per run with config snapshot, results and notes.
- `training/` - trajectory conversion and LoRA training (phase 2).
- `kaggle/` - notebooks for free-tier GPU evaluation and training.
- `paper/` - paper-track write-up.

## Constraints I chose
$0 cloud spend (Kaggle free GPU hours only), a 16 GB laptop GPU as the dev box, no proprietary-model distillation.
