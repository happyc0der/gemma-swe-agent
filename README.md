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
| 09-26 | Kaggle | day 3: v4.1, thinking off, 5.5 min / task | **failed: "Notebook Exceeded Allowed Compute"** (12 h sequential cap) |
| 09-27 | **Kaggle** | day 4: v4.3, thinking off, 3.5 min / task | **0.06** (first non-zero; rank 284/543; scored in ~7.5 h) |
| 09-28 | **Kaggle** | day 5: same, 4.5 min / task | **0.10** |
| 09-29 | **Kaggle** | day 6: same, 5.0 min / task | **0.08** (within noise of day 5; runs finish in ~6.5 h, so the cap no longer binds) |
| 09-30 | **Kaggle** | day 7: day 5 + temperature 0.2, top_k 40 | **0.10** (ties day 5; temperature does not move the score) |
| 09-26 | Kaggle T4x2, real 31B | day-4 config: v4.3, 4.5 min | 1/33; 12.1 tool calls per task, 32/33 hit the time budget at ~12 tok/s |
| 09-26 | MSI proxy, official harness, 33 holdout | v4.1 / v4.2 / v4.3 (no `read_file` tool) / organizers' sample prompt without adapters | 5 / 4 / 5 / 2 of 33, and v4.3 + analyzer sub-agent 5/33 (noise band +/-3; union of solved tasks 9/33); v4.3 has 0 rejected calls and 17 clean endings vs 9 for v4.1 |
| 10-01 | **Kaggle** | day 8: prompt v4.4 (~25-call plan, submit_patch once the repro passes), temp 0.2, 4.5 min / 40 calls | **no score** (blank after 54 h; probable failure, cause unconfirmed) |
| 10-03 | **Kaggle** | day 9: v4.4 at 3.5 min | **0.06** (finished within ~7 h); best 0.10 = rank 418/1559 on 10-03 |
| 10-03 | CPU kernel: official harness + scorer-like sandbox (`kaggle/faithful_sandbox.py`), 33 holdout | gold patches / no patch | **33/33 / 0/33**, ~11 s per verification, 0 GPU hours |
| 10-03 | **Faithful eval**: Kaggle T4x2, real 31B (llama.cpp, thinking off), official Evaluator, 16 holdout tasks, time x3 | prompt v4.5, temp 0.2 | 7/16 (verbatim loops of up to 23 identical calls at temp 0.2) |
| 10-03 | faithful eval | v4.6: temp 0.7, repro cap, edit by call 10, no-repeat rule | **8/16** (looping tasks 3 -> 0, median first edit call 33 -> 18) |
| 10-03 | faithful eval | v4.7: timeout-wrapped scripts, follow issue-described designs | 8/16 (tasks without an edit 3 -> 1, hung commands 2 -> 0) |
| 10-03 | faithful eval | v4.8: empty grep means not found | 8/16, same tasks as v4.7; exact repeat calls 77 -> 130 (27% of calls), so day 10 = v4.7 at 4.5 min |
| 10-03 | faithful eval | v4.9: one-line note before every call | **7/16**: with thinking off the model never wrote a note; it emitted empty thought-channel markers instead (7 replies with no tool call), so the idea is dropped |
| 10-04 | faithful eval | v5.0n: grep instead of paging, behaviour before docstrings, fix sibling functions, never resend malformed calls | **9/16** (best: all earlier solves kept plus a never-solved task; fewest repeats, timeouts and minutes); day 11 |
| 10-04 | **Kaggle** | day 10: prompt v4.7, temp 0.7, 4.5 min / 40 calls | **0.06** (4 of the 58 public tasks; v4.3 scored 6 and 6 at the same budget, so the newer prompts may do worse on the hidden repos; day 11 = v5.0n tests it again) |
| 10-05 | **Kaggle** | day 11: prompt v5.0n, temp 0.7, 4.5 min / 40 calls | **0.10** (6/58 tasks; +2 over v4.7 at the same budget, equal to our best) |
| 10-06 | **Kaggle** | day 12: v5.0n with 5.0 min / 50 calls | **0.06** (4/58). Across all 8 scored days: 4-6 tasks, mean 4.9, sd 1.0, i.e. within run-to-run noise; 4.5 min averages best (5.5 tasks over 4 runs) |
| 10-08 | faithful eval | v5.0n with thinking on | **6/16** vs 9/16 off: far fewer loops, but 9 of 16 tasks hit the session timeout; not submitted |
| 10-08 | Kaggle T4x2 LoRA gate | QLoRA r=16 on the 31B QAT checkpoint (4-bit) | fits only up to **3,072 tokens** (60 s/step); the agent's trajectories are 7k-17k tokens, so LoRA is not viable on free T4s |

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
