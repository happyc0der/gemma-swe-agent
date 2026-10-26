# Measure what the scorer measures: a $0 faithful evaluation loop, a failure taxonomy, and leaderboard noise for a Gemma 4 31B software agent

Keshav Rajput (Kaggle `dankaxon`, GitHub `happyc0der`). Solo entry, Google - The Gemma 4 Developer Agent Competition.
Code and every run: https://github.com/happyc0der/gemma-swe-agent

**Status: first draft, 2026-10-25** (written by the daily routine from `paper/outline.md` and `experiments/`; numbers
are final up to that date; sections marked TODO are filled in before 2026-11-09).

## Abstract

We built and ran a software-engineering agent on the competition's fixed model (Gemma 4 31B, W4A16) with a $0 budget:
free Kaggle GPU hours only, no proprietary-model distillation. Three results. (1) A faithful offline evaluation is
buildable on free compute: a patched copy of the organizers' sandbox reproduces the scorer's verification exactly
(gold patches 33/33, no patch 0/33 on a 33-task holdout), and the real 31B runs through the official Evaluator on a
free T4 pair. (2) Checking each diagnosis against that faithful loop overturned three plausible root causes, and the
agent's traces give a measured failure taxonomy whose dominant mode is not reasoning but tool-call hygiene: malformed
`edit_file` calls that the harness rejects without charging the call budget, resent dozens of times. (3) Noise sets
the limits of what anyone can learn from this leaderboard: identical files differ by about +/-3 of 58 public tasks
between runs, eleven thinking-off variants span 7-14 of 33 offline, and the one change that clearly moved the public
score (thinking on, from a public reference bundle we adopted with credit) is exactly the one our T4 loop cannot
evaluate. We report these as a method and a set of cautions for agent work on a fixed model.

## 1. Setting

- Task: fix real GitHub issues in Python repositories (fastapi, requests, rich and others) inside an offline sandbox;
  a task counts when the hidden tests pass. Public leaderboard = 58 tasks, score = solved/58 truncated to two decimals.
- Fixed model `gemma-4-31b-it-qat-w4a16-ct`, served by the organizers on 4x L4. Entrants submit only a declarative
  ADK agent (YAML config, prompt, tool settings, budgets): no weights unless LoRA adapters, one submission per day,
  12 h runtime cap for the whole scoring run.
- Our constraints: $0 cloud spend (Kaggle's 30 GPU h/week of T4 x2), a 16 GB laptop GPU as dev box, no Claude/Gemini
  generated training data.

## 2. A faithful offline evaluation on free compute

**Sandbox fidelity.** The organizers' subprocess sandbox differs from the scorer's container: host site-packages
leak in, the wrong Python runs, test dependencies are missing. `kaggle/faithful_sandbox.py` builds a uv CPython 3.13
venv from the competition wheels, installs each snapshot editable and replays the dataset setup. On a CPU-only Kaggle
kernel it gives **gold 33/33 and no-patch 0/33** on our holdout (seed 20260924, `experiments/splits.json`), ~11 s per
verification, 0 GPU hours (`experiments/2026-10-03-faithful-sandbox.md`). Sandbox commands are capped at 4 GB like the
scorer's container after an agent's reproduction script grew a string exponentially and OOM-killed the host.

**Model fidelity.** The real 31B (llama.cpp Q4_0, pinned build) runs on the free T4 pair through the official
Evaluator (`kaggle/eval_faithful/run.py`), with a canary task that must pass before a run counts. T4s generate about
4-12 tokens/s, so we scale every time budget by 3 and run with **thinking off**; a 33-task run costs ~4.3-4.5 GPU h
(`experiments/kaggle_gpu_hours.md`). This makes the loop faithful for thinking-off configurations only (Section 6).

**Harness fidelity.** Before the harness was released we wrote `swelite`, a re-implementation; once the wheelhouse
appeared, every config check moved to the official code, and `scripts/compile_check.py` compiles each variant with
the exact released harness before it is staged (`docs/harness-fidelity.md` lists every difference we found).

## 3. Three wrong root causes, each caught by checking against the real thing

1. **"`read_file` receives string line numbers."** On a newer vLLM serving a 12B proxy, 20 of 24 ranged `read_file`
   calls were rejected, and three 0.00 scores seemed explained. A replica of the scorer's exact stack (vLLM 0.19.1,
   real 31B with CPU offload, ADK 1.36.1) passes integers: a proxy artefact.
2. **"Day 3 overran the 12 h cap, so cut the per-task budget."** The Kaggle CLI hides the error text; the API's
   `errorDescription` (`scripts/submission_errors.py`) said resource/capacity, and later failures were "unhandled
   error" and a Kaggle system error. We had cut the budget for a cause that never happened. Lesson repeated on
   10-22: an "unhandled error" with files that had completed 11 times elsewhere was run-specific; the identical
   retry completed (9/58).
3. **"An empty grep is reported as an error."** Piped through `head`, a search with no hits returns status ok and
   exit 0; a prompt rule describing the error case taught the model nothing (`experiments/2026-10-03-faithful-v48`).
   Without the pipe, `grep` exits 1 and the harness reports `status: error` with empty output, which is the case the
   current candidate addresses (Section 5).

## 4. Failure taxonomy of the 31B agent, measured from traces

Measured with `scripts/faithful_metrics.py` and small trace scripts over the faithful runs (thinking off).

| failure mode | evidence |
|---|---|
| verbatim loops at temperature 0.2 | up to 23 identical consecutive calls (v4.5); gone at temperature 0.7 |
| no scratchpad | 0 of ~1,900 steps contain text before the tool call; asking for a one-line note produced empty thought-channel markers and replies with no tool call (7/16 vs 8/16) |
| malformed `edit_file` calls resent | a stray backtick swallows `old_string`; the harness rejects the call **without charging `max_tool_calls`**, so the loop runs to the 80-turn cap or the session timeout. Budget-fit prompt, thinking off: 164 `edit_file` calls, 128 missing `old_string`, 2 tasks at the 80-turn cap (kernel v23) |
| no-match searches repeated | 81 of 396 `run_command` calls (20%) were greps with no hits, 30 of them exact repeats, in 12 tasks (11 unresolved), and in 5 of the 6 tasks that ended with no edit (v23, `scripts/count_nomatch_greps.py`) |
| paging through files | up to 21 consecutive 60-line reads (v4.x); gone once the prompt says grep -n first |
| plumbing before behaviour | signatures and docstrings edited, core logic never reached |
| sibling misses | fixing `append` but not its identical sibling `append_text`; a sibling rule recovered rich_3480 |
| silent no-op fix scripts | 28 of 70 heredoc fix scripts never reached their write line (the model reasoned in comments inside the heredoc); a fixed `edit()` helper cut them to 4 but produced 35 assert failures |
| `submit_patch` typed into the shell | 17 tasks when `edit_file` was removed; one prompt line cut it from 24 calls to 8 |
| hidden-test infinite loops | verification exhausting host memory (our OOM kills) |

Two patterns matter for anyone writing prompts for this model. First, **compliance is low and must be measured, not
assumed**: the harness's own `budget_warning` (shown when <= 10 calls remain) is the one nudge the model reliably
obeys (it submits after the warning in 21-22 of 23 tasks), while added prompt bullets are followed rarely: "make the
edit on your next call after the warning" 3 of 23 times (bf-warn), "after an `edit_file` error use one Python fix
script" after 6 of 236 errors, in 2 tasks (bf-editfb, kernel v25). Second, **a rule can move a failure instead of
removing it**: removing `edit_file` removed malformed calls (0) but sent `submit_patch` to the shell; an edit-first
rule turned reproduction loops into search loops (11 no-edit tasks vs 4). The one bullet that helped offline stated
a fact about the environment rather than an instruction about behaviour: "a grep with no hits comes back as `status:
error` with empty output; the text is absent" (bf-nomatch, kernel v26) cut exact repeats of no-match searches from
30 to 20, total agent time by 24%, and scored 11/33 against the base's 9/33 (a single paired run; its LB days follow).

TODO: occurrence table per run for the main modes (v5.0n, v5.8, budget-fit-off), from the existing trace scripts;
add the public task-level dataset of 692 runs (dmitriigluzdov, CC BY 4.0) as an external check, with credit.

## 5. Prompt iteration offline, and its resolution

Thinking-off variants on the 33-task holdout (set AB), each a single faithful run:

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
Single offline runs therefore detect only large effects; we used them to **reject** changes whose mechanism visibly
failed in the traces (low compliance, a failure that moved) rather than to rank close variants. Over the full 33
tasks, 16 have never been solved by any variant.

## 6. The leaderboard: noise, and the change we could not evaluate offline

**Noise.** Our thinking-off v5.0n at 4.5 min scored 6, 6, 5, 7, 6, 4, 6, 7, 5 of 58 over nine days (mean 5.8, sd 1.0).
A public census of 274 notebooks (dariushafshar, "Most-Run Public Config Averages", dataset
gemma-4-agent-public-config-draws, 10-22) found a pooled within-config sd of 1.56 tasks across 29 repeated draws of
six identical file sets: 95% of single draws fall within about +/-3 tasks of the config mean. No public file set with
>= 3 draws averages above 10.0, and the four such sets span 9.25-10.00, a range narrower than one draw's noise. Under a
normal model, the best of ten draws of one config sits ~2.4 tasks above its mean, which is enough to explain the
highest public scores without any better config.

**The change that mattered.** On 10-21 we adopted the public "Budget-Fit" reference bundle (verracodeguacas, Apache
2.0, credited in `experiments/variants/pub-budget-fit.CREDIT.md`): the official starter prompt, temperature 0.2,
thinking on with a 4096-token budget, 8 min / 28 calls / 80 turns / 240 s per task. We verified by hash that our files
equal the most-run public file set (10 public draws, mean 10.00). Our own draws of the same files: 10, 9, 8, 9 (mean 9.0)
plus one run-specific unhandled error; our best thinking-off configs averaged 5.8-7.0. Offline, with thinking off, the
same bundle scored 9/33 against 14/33 for our v5.8: **the offline loop ranked the two in the opposite order to the
leaderboard**, because the variable that matters (thinking on) is the one T4 throughput forced us to remove. An early
thinking-on attempt on our own prompt (v5.0n, 4096 tokens, 8 min / 28 calls) scored 7/58, within noise of its
thinking-off runs, so the gain belongs to the bundle as a whole, not to thinking alone.

**Runtime.** The 8-minute family fits the 12 h cap only because most tasks stop early: 116 tasks at the full cap would
take ~15.7 h. A related public bundle ("contract-first") exceeded the 12 h cap for us on its first run and was dropped.

TODO: final LB table for the base and every candidate through 11-08; whether bf-nomatch (Section 4's no-match grep
finding; offline 11/33 vs 9/33, LB days from 10-27) held up on the leaderboard; bf-noedit (no `edit_file`) screen.

## 7. What we would do differently

- Spend the first GPU hours on a stack that can run the scorer's real configuration (thinking on), even on fewer
  tasks, before optimising prompts on a configuration the scorer will not use.
- Treat every leaderboard number as one draw: log configs with a hash, pool repeated draws, and pick finals by mean.
- Read the error text behind every failed run before changing a budget.

## 8. Negative results

- LoRA on free T4s: QLoRA r=16 on the 31B QAT checkpoint fits only up to 3,072 tokens (60 s/step); trajectories are
  7k-17k tokens, so not viable at $0.
- Provided code-intelligence tools: only 69 of 256 public snapshots have both a non-empty graph and embeddings, and
  the model never called them.
- ADK events compaction never fired inside a task; on the 12B proxy a context-budget prompt section moved context
  overflow from 12/33 to 2/33 tasks, but the 31B with the budget-fit prompt had 0 overflows in 33 tasks.

## Reproducibility

Every faithful run has `task_results.jsonl`, `summary.json`, `run.log` and `notes.md` under `experiments/`; every daily
submission is logged with its config snapshot, score and hidden error text in `experiments/kaggle_submissions.md`, with
a per-config tally in `experiments/lb_configs.md`. Kaggle kernel: `dankaxon/gemma4-faithful-eval`.

## Credits

Budget-fit reference bundle: verracodeguacas (Apache 2.0). Public config census: dariushafshar. Task-level run dataset
cited in Section 4: dmitriigluzdov (CC BY 4.0). Harness and data: the competition organizers.
