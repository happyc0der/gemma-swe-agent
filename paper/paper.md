# Measure what the scorer measures

**A $0 faithful evaluation loop, a measured failure taxonomy, and leaderboard noise for a Gemma 4 31B software agent**

Keshav Rajput (Kaggle `dankaxon`, GitHub `happyc0der`). Solo entry, Google - The Gemma 4 Developer Agent Competition.
Code, data and every run: https://github.com/happyc0der/gemma-swe-agent

## Abstract

We built and ran a software-engineering agent on the competition's fixed model (Gemma 4 31B, W4A16) with a $0 budget:
free Kaggle accelerator hours only, no proprietary-model distillation. Three results. (1) A faithful offline evaluation
is buildable on free compute: a patched copy of the organizers' sandbox reproduces the scorer's verification exactly
(gold patches 33/33, no patch 0/33 on a 33-task holdout), and the real 31B runs through the official Evaluator on a
free T4 pair. (2) Checking each diagnosis against that loop overturned three plausible root causes, and the traces
give a measured failure taxonomy whose dominant mode is tool-call hygiene, not reasoning: malformed `edit_file` calls
that the harness rejects without charging the call budget, resent dozens of times. Prompt rules that tell the model
how to behave are rarely obeyed (3 of 23 times for the most direct one). (3) Noise sets the limit of what this
leaderboard can teach: identical files differ by about +/-3 of 58 public tasks between runs, and the one change that
clearly moved the public score (thinking on) is exactly the one our T4 loop could not evaluate. We report the method,
the taxonomy and these cautions for agent work on a fixed model.

## 1. Introduction

The task is to fix real GitHub issues in Python repositories (fastapi, requests, rich and others) inside an offline
sandbox; a task counts when hidden tests pass. The public leaderboard has 58 tasks, scored as solved/58 truncated to
two decimals. The model is fixed (`gemma-4-31b-it-qat-w4a16-ct`, served by the organizers on 4x L4). Entrants submit
only a declarative ADK agent (YAML config, prompt, tool settings, budgets), one submission per day, with a 12 h cap on
the whole scoring run. Our constraints: $0 cloud spend (Kaggle's weekly free T4 x2 and TPU v5e-8 hours), a 16 GB
laptop GPU as dev box, and no Claude- or Gemini-generated training data.

With the model frozen, every question is about the agent around it, and each answer is only as good as its
measurement. The leaderboard gives one noisy draw per day; offline runs on free hardware differ from the scorer in
sandbox, serving stack and, it turns out, the configuration that matters most. We contribute a faithful offline
evaluation (Section 2), three diagnoses overturned by it (Section 3), a trace-measured failure taxonomy with an
instruction-compliance measurement (Section 4), and a noise model of offline runs and the leaderboard, plus a
thinking-on lane on a free TPU (Sections 5-6).

## 2. A faithful offline evaluation on free compute

**Sandbox fidelity.** The organizers' subprocess sandbox differs from the scorer's container: host site-packages
leak in, the wrong Python runs, test dependencies are missing. `kaggle/faithful_sandbox.py` builds a uv CPython 3.13
venv from the competition wheels, installs each snapshot editable and replays the dataset setup. On a CPU-only Kaggle
kernel it gives **gold 33/33 and no-patch 0/33** on our holdout (seed 20260924, `experiments/splits.json`), ~11 s per
verification, 0 GPU hours. Sandbox commands are capped at 4 GB, like the scorer's container.

**Model fidelity.** The real 31B (llama.cpp Q4_0, pinned build) runs on the free T4 pair through the official
Evaluator (`kaggle/eval_faithful/run.py`). A canary task with the fixed base configuration must pass before a run
counts. T4s generate 4-12 tokens/s, so we scale every time budget by 3 and run
with **thinking off**; a 33-task run costs ~4.3-4.5 GPU h (`experiments/kaggle_gpu_hours.md`). The loop is therefore
faithful for thinking-off configurations only (Section 6).

**Harness fidelity.** Every check uses the released harness code; `scripts/compile_check.py` compiles each variant with the
released harness before it is staged (`docs/harness-fidelity.md` lists every difference we found).

## 3. Three wrong root causes, each caught by checking against the real thing

1. **"`read_file` receives string line numbers."** On a newer vLLM serving a 12B proxy, 20 of 24 ranged `read_file`
   calls were rejected, and three 0.00 scores seemed explained. A replica of the scorer's stack (vLLM 0.19.1, real
   31B with CPU offload, ADK 1.36.1) passes integers: a proxy artefact.
2. **"Day 3 overran the 12 h cap, so cut the per-task budget."** The Kaggle CLI hides the error text; the API's
   `errorDescription` (`scripts/submission_errors.py`) said resource/capacity. We had cut the budget for a cause that
   never happened.
3. **"An empty grep is reported as an error."** Piped through `head`, a search with no hits returns status ok and
   exit 0; a prompt rule describing the error case taught the model nothing. Without the pipe, `grep` exits 1 and the
   harness reports `status: error` with empty output, the case a later candidate addressed (Section 4).

## 4. Failure taxonomy of the 31B agent, measured from traces

Measured with `scripts/faithful_metrics.py` and small trace scripts over the faithful runs (thinking off).

| failure mode | evidence |
|---|---|
| verbatim loops at temperature 0.2 | up to 23 identical consecutive calls; gone at temperature 0.7 |
| no scratchpad | 0 of ~1,900 steps contain text before the tool call; asking for a one-line note produced empty thought-channel markers and replies with no tool call (7/16 vs 8/16) |
| malformed `edit_file` calls resent | a stray backtick swallows `old_string`; the harness rejects the call **without charging `max_tool_calls`**, so the loop runs to the 80-turn cap or the timeout. Budget-fit prompt: 164 `edit_file` calls, 128 missing `old_string` |
| no-match searches repeated | 81 of 396 `run_command` calls (20%) were greps with no hits, 30 of them exact repeats, in 12 tasks (11 unresolved) |
| paging through files | up to 21 consecutive 60-line reads; gone once the prompt says grep -n first |
| plumbing before behaviour | signatures and docstrings edited, core logic never reached |
| sibling misses | fixing `append` but not its identical sibling `append_text` |
| silent no-op fix scripts | 28 of 70 heredoc fix scripts never reached their write line; a fixed `edit()` helper cut them to 4 but produced 35 assert failures |
| `submit_patch` typed into the shell | 17 tasks when `edit_file` was removed; one prompt line cut it from 24 calls to 8 |

Two patterns matter for anyone writing prompts for this model. First, **compliance is low and must be measured**: the
harness's own `budget_warning` (shown when <= 10 calls remain) is the one nudge the model reliably obeys (it submits
after it in 21-22 of 23 tasks), while added prompt bullets are followed rarely: "make the edit on your next call
after the warning" 3 of 23 times (bf-warn), "after an `edit_file` error use one Python fix script" after 6 of 236
errors (bf-editfb). Second, **a rule can move a failure instead of removing it**: removing `edit_file` removed
malformed calls but sent `submit_patch` to the shell; an edit-first rule turned reproduction loops into search loops
(11 no-edit tasks vs 4). The bullet that looked best offline stated a fact about the environment rather than an
instruction: "a grep with no hits comes back as `status: error` with empty output; the text is absent" (bf-nomatch)
cut exact no-match repeats from 30 to 20 and agent time by 24%, scoring 11/33 against the base's 9/33.

Occurrence per run on the 33-task holdout, thinking off ("exact repeats" = a call identical in name and arguments to
an earlier call in the same task; `scripts/taxonomy_table.py`):

| run | solved | agent min | edit_file (no old_string) | run_command | no-match greps (repeats) | exact repeats | submit_patch in shell | at call cap | at turn cap | empty patches |
|---|---|---|---|---|---|---|---|---|---|---|
| v5.8 prompt (no edit_file) | 14/33 | 228 | 0 (0) | 905 | 37 (1) | 128 | 6 | 3 | 0 | 6 |
| budget-fit-off | 9/33 | 220 | 164 (128) | 396 | 81 (30) | 281 | 0 | 3 | 2 | 6 |
| bf-warn-off | 10/33 | 234 | 328 (287) | 358 | 49 (2) | 389 | 0 | 1 | 4 | 8 |
| bf-editfb-off | 7/33 | 228 | 259 (229) | 433 | 65 (5) | 347 | 0 | 2 | 3 | 10 |
| bf-nomatch-off | 11/33 | 167 | 184 (149) | 401 | 85 (20) | 282 | 0 | 2 | 2 | 8 |

Every budget-fit variant spends 78-88% of its `edit_file` calls on calls with no `old_string`.

**When the first edit lands.** Over 99 official-harness tasks of the budget-fit prompt, thinking off (three 33-task
runs: 9, 12 and 9 solved), tasks whose first source edit came by call 12 resolved 24 of 37 (65%), tasks that edited
later 6 of 45 (13%), and the 17 that never edited 0. Tasks finishing within 14 calls resolved 14 of 18 (78%), those
running to the 80-turn cap 0 of 18. The prompt already says "by your 12th tool call you must have edited a source
file", yet the median first edit is call 17-20: the compliance point again, on a different instruction. Part of the
correlation is selection (easy tasks are edited early), so this maps where the misses are rather than proving that an
earlier edit would convert them. Two independent public analyses on other harness setups agree (Section 7).

## 5. Prompt iteration offline, and its resolution

Thinking-off variants on the 33-task holdout, each a single faithful run:

| variant | change | solved /33 |
|---|---|---|
| v5.0n | grep instead of paging, behaviour before docstrings, siblings, never resend malformed calls | 13 |
| v5.4 | edit before any script | 13 |
| v5.5 | + harness `read_file` tool | 9 |
| v5.6 | no `edit_file` (fix scripts) | 11 |
| v5.7 | + "submit_patch is a tool" | 12 |
| v5.8 | + budget-warning protocol | 14 |
| v5.9 | fixed `edit()` helper | 12 |
| v6.0 | indentation-tolerant helper | 14 |
| pub-budget-fit-off | public budget-fit bundle, thinking off | 9 |
| bf-warn-off | + budget-warning bullet | 10 |
| bf-editfb-off | + edit-error fallback bullet | 7 |

Eleven variants span 7-14 (mean 11.3, sd 2.3), while the binomial sd of one 33-task run at this rate is ~2.8 tasks.
Single offline runs detect only large effects, so we used them to **reject** changes whose mechanism visibly failed in
the traces (low compliance, a failure that moved) rather than to rank close variants. 16 of the 33 tasks were never
solved by any variant.

## 6. The leaderboard: noise, and the change we could not evaluate offline

**Noise.** Our thinking-off v5.0n scored 6, 6, 5, 7, 6, 4, 6, 7, 5 of 58 over nine days (sd 1.0). A public census of
274 notebooks (dariushafshar, 10-22) found a pooled within-config sd of 1.56 tasks over 29 repeated draws of six
identical file sets: 95% of single draws fall within about +/-3 tasks of the config mean. No public file set with >= 3
draws averaged above 10.0. The best of ten draws of one config sits ~2.4 tasks above its mean (normal model), enough to
explain the highest public scores without a better config. We therefore judge configs only by their mean
over at least three runs, interleaved with base days, and promote a candidate only at base + 1.5 tasks.

**The change that mattered.** On 10-21 we adopted the public "Budget-Fit" bundle (verracodeguacas, Apache 2.0): the
official starter prompt, temperature 0.2, thinking on with a 4096-token budget, 8 min / 28 calls / 80 turns / 240 s
per task. We verified by hash that our files equal the most-run public file set (10 public draws, mean 10.0). Offline,
with thinking off, the same bundle scored 9/33 against 14/33 for our v5.8: **the offline loop ranked the two in the
opposite order to the leaderboard**, because the variable that matters (thinking on) is the one T4 throughput forced
us to remove. Our own prompt with thinking on scored 7/58, within noise of its thinking-off runs, so the gain belongs
to the bundle as a whole, not to thinking alone. The bundle fits the 12 h cap only because most tasks stop early (116
tasks at the full 8 min would take ~15.7 h); a related public bundle exceeded the cap on its first run.

**Leaderboard by config, through 2026-11-08** (solved of 58 public tasks per completed run; full log in
`experiments/kaggle_submissions.md`):

| config | draws | n | mean |
|---|---|---|---|
| v5.0n (our prompt, tuned on the thinking-off loop) | 6, 4, 6, 6, 5, 7, 6, 4, 6, 7, 5, 7, 7 | 13 | 5.85 |
| v5.8 | 7 | 1 | 7.0 |
| pub-budget-fit (base) | 10, 9, 8, 9, 11, 10, 11, 9, 10, plus one run-specific error | 9 | 9.67 |
| bf-nomatch (no-match grep bullet) | 8, 7; dropped | 2 | 7.5 |
| bf-think2k (thinking budget 2048) | 10, 10 | 2 | 10.0 |
| bf-t10 (temperature 1.0 / top_p 0.95 / top_k 64) | 8, 10 | 2 | 9.0 |
| bf-think1k (thinking budget 1024) | 12 | 1 | 12.0 |

bf-nomatch is the clearest case against the thinking-off proxy: level offline (31/99 vs 30/99 for the base's
thinking-off twin, with 12% less agent time), yet both its draws fell below the base mean. Further runs of bf-think2k,
bf-t10 and bf-think1k are scoring as this is written.

**A thinking-on lane on a free TPU v5e-8.** To close the gap we served the 31B with vllm-tpu 0.32.0 (bf16 QAT
weights): 64 tok/s decode on an 11.7k-token prompt, thinking and tool parsing correct, so time budgets need scaling by
only ~0.5. Two traps are worth recording. Two runs died with no output until an early-exit diagnostic showed why: writing 62.6 GB of weights to a disk sustaining ~25 MB/s leaves a ~60 GB
dirty-page backlog that stalls all I/O; holding the weights in /dev/shm fixed it (download 52 s). Then every model call
failed: an unpinned `pip install litellm` pulled a release importing `mcp.types.CacheableResult` (mcp >= 2.2), while
the wheelhouse's google-adk requires mcp < 2; pinning litellm to the compiled version fixed it. The backend also does
not enforce `thinking_token_budget` (a budget of 64 returned 542 reasoning tokens), so this lane can compare sampling
and prompt changes but not thinking budgets.

## 7. Related work

SWE-bench (Jimenez et al., 2024) defined issue resolution judged by hidden tests, the task format here. SWE-agent
(Yang et al., 2024) showed that the agent-computer interface (tool design, feedback format, guardrails such as
rejecting malformed edits) drives performance; our taxonomy is a measurement of that interface for one fixed open
model, and finds that a guardrail which rejects a call without charging the budget creates a loop. Agentless (Xia et
al., 2024) argued that a fixed localize-repair pipeline can match free-form agents; our first-edit result (late edits
rarely resolve) is consistent with localization being the bottleneck. Unlike open platforms such as OpenHands (Wang et al., 2025), we had to reproduce the organizers'
harness exactly. Madaan et al. (2024) quantify seed variance in LLM benchmarks; Section 6 gives the same kind of
estimate for an agentic leaderboard, where variance comes from sampling over long multi-turn trajectories.

Within the competition, public work agrees with ours (author-reported; we did not re-run it). Dmitrii Gluzdov's
dataset of 692 local 31B runs (CC BY 4.0), as summarised by Aleksei Provorov (`leoprovorov/single-agent-anytime-patch`):
194 runs (28%) ended with no patch, and a thinking-on prompt resolved 37 of 71 runs using at most 14 calls against 2 of
43 using 15-20. Fabrian Ivan Prasetya (`fabrianivan/gemma-4-swe-agents-three-paradoxes-ca-hgr`), over 487
trajectories: resolution fell from 48% with no history compaction to 26% after one and 13% after two (compaction
above 14,336 context tokens drops the verbatim issue text), and runs whose first edit landed in steps 5-12 resolved
43-48% against 24% later. The same author reports that changing only sampling from 0.2 to 1.0 moved one leaderboard
draw from 0.18 to 0.24, which led to our bf-t10 candidate; its two draws so far (8, 10) are within base noise.

## 8. Lessons and negative results

- First run the scorer's real configuration offline, even on fewer tasks; then optimise.
- Treat every leaderboard number as one draw: log configs by hash, pool draws, pick finals by mean.
- State facts about the environment rather than behavioural rules, and count compliance in traces.
- LoRA on free T4s: QLoRA r=16 on the 31B fits only up to 3,072 tokens (60 s/step); trajectories are 7k-17k tokens.
- Provided code-intelligence tools: only 69 of 256 public snapshots have both a non-empty graph and embeddings, and
  the model never called the graph tools (0 of 2,683 calls over 99 tasks).
- On a 12B proxy a context-budget prompt section moved context overflow from 12/33 to 2/33 tasks, but the 31B with
  the budget-fit prompt had 0 overflows in 33 tasks.

## Reproducibility

Every faithful run has `task_results.jsonl`, `summary.json`, `run.log` and `notes.md` under `experiments/`; every
daily submission is logged with its config snapshot, score and hidden error text in
`experiments/kaggle_submissions.md`, with a per-config tally in `experiments/lb_configs.md` and accelerator use in
`experiments/kaggle_gpu_hours.md`. Kernels: `kaggle/eval_faithful/` (T4) and `kaggle/eval_tpu/` (TPU).

## References

- C. E. Jimenez, J. Yang, A. Wettig, S. Yao, K. Pei, O. Press, K. Narasimhan. SWE-bench: Can Language Models Resolve
  Real-World GitHub Issues? ICLR 2024.
- J. Yang, C. E. Jimenez, A. Wettig, K. Lieret, S. Yao, K. Narasimhan, O. Press. SWE-agent: Agent-Computer Interfaces
  Enable Automated Software Engineering. NeurIPS 2024.
- C. S. Xia, Y. Deng, S. Dunn, L. Zhang. Agentless: Demystifying LLM-based Software Engineering Agents. arXiv:2407.01489, 2024.
- X. Wang et al. OpenHands: An Open Platform for AI Software Developers as Generalist Agents. ICLR 2025.
- L. Madaan et al. Quantifying Variance in Evaluation Benchmarks. arXiv:2406.10229, 2024.
- Kaggle community work: verracodeguacas (Budget-Fit bundle, Apache 2.0); dariushafshar (public config census,
  dataset `gemma-4-agent-public-config-draws`); dmitriigluzdov (`gemma-4-serving-and-lora-verification-kit`, CC BY 4.0);
  leoprovorov; fabrianivan. Harness and data: the competition organizers.
