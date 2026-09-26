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
| 09-26 | MSI proxy (vLLM 0.30), **official `swegemma` harness** (wheelhouse) | prompt v4.1 | 20 of 24 `read_file` calls rejected (string line numbers); later shown to be a proxy artefact |
| 09-26 | **Scorer replica on the MSI**: vLLM 0.19.1 + real 31B (CPU offload) + ADK 1.36.1 | tool-call probe | read_file receives integers; the string-argument failure does not occur on the scorer's stack |
| 09-26 | Kaggle T4x2, real 31B, 32k context | prompt v4.2 | 2/33; every task hit the 5.5 min budget at ~12 tok/s, so T4 runs only bound prompts from below |
| 09-26 | MSI proxy, official harness, 33 holdout | v4.1 / v4.2 / v4.3 (no `read_file` tool) / organizers' sample prompt without adapters | 5 / 4 / 5 / 2 of 33, and v4.3 + analyzer sub-agent 5/33 (noise band +/-3; union of solved tasks 9/33); v4.3 has 0 rejected calls and 17 clean endings vs 9 for v4.1 |

Key findings: the organizers released the real harness on 09-25 (`harness/official/`, from the Kaggle wheelhouse dataset). Running it against my 12B proxy made every ranged `read_file` fail, which I first took for the cause of three 0.00 scores; a replica of the scorer's exact stack (vLLM 0.19.1 serving the real 31B, ADK 1.36.1) showed read_file works there, so that was a proxy artefact and the 0.00 cause is still open. Also: the competition's 31B runs on Kaggle's free T4 pair only through llama.cpp (vLLM's INT4 kernels need Ampere); ADK never compacts context inside a task, so trajectories die at the 32k window after ~20 full-size tool outputs; low temperature causes verbatim retry loops; the Ollama proxy ignores `max_tokens` and has no thinking budget, so vLLM is the only faithful local proxy.

## Layout
- `submission/` - exactly what gets zipped and uploaded (YAML agent config, prompts, skills, adapters).
- `harness/` - `swelite`, a local re-implementation of the `swegemma` evaluator written before it was released (Docker/subprocess sandboxes, the 9 tools, ADK compile, verification, failure taxonomy), and `harness/official/`, the organizers' released source (swegemma 0.2.7, adk-submission 0.2.11, adk-eval-core 0.1.0) used for all config checks since 09-26; `docs/harness-fidelity.md` lists every difference.
- `experiments/` - one folder per run with config snapshot, results and notes.
- `training/` - trajectory conversion and LoRA training (phase 2).
- `kaggle/` - notebooks for free-tier GPU evaluation and training.
- `paper/` - paper-track write-up.

## Constraints I chose
$0 cloud spend (Kaggle free GPU hours only), a 16 GB laptop GPU as the dev box, no proprietary-model distillation.
