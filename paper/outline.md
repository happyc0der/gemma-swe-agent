# Paper-track outline (due 2026-11-12)

**Working title: "Measure what the scorer measures: a $0 evaluation loop and failure taxonomy for a thinking-off
Gemma 4 31B software agent"**

Rewritten 2026-10-08. The 2026-09-26 outline led with an `any_of` tool-schema failure; that was a proxy artefact
(the scorer's own stack passes integers, see `docs/harness-fidelity.md`) and is now a cautionary example, not a claim.

## Claims and their evidence

1. **A faithful offline evaluation is buildable on free compute.** The organizers' subprocess sandbox differs from
   the scorer's Docker image (host site-packages, wrong Python, missing test deps). Patching it
   (`kaggle/faithful_sandbox.py`: uv CPython 3.13 venv, competition wheels, editable install, dataset setup) gives
   gold 33/33 and no-patch 0/33 on the holdout on a CPU-only Kaggle kernel (`experiments/2026-10-03-faithful-sandbox.md`).
   The real 31B runs through the official Evaluator via llama.cpp on the free T4 pair, thinking off, time x3,
   ~2.5 GPU h per 16-task run (`kaggle/eval_faithful/`).
2. **Three wrong root causes, each caught by checking against the real thing.**
   - `read_file` string line numbers: an artefact of a newer vLLM + 12B proxy; a scorer replica (vLLM 0.19.1 + real 31B)
     passes integers.
   - "Day 3 overran the 12 h cap": the Kaggle API's `errorDescription` (hidden by the CLI) says it was a
     resource/capacity error; day 8 was an unhandled error, day 13 a Kaggle system error. The per-task budget had been
     cut for a cause that never happened (`experiments/kaggle_submissions.md`, `scripts/submission_errors.py`).
   - The v4.8 "empty grep" rule described the wrong output: piped through `head`, an empty search returns
     status ok / exit 0, not an error (`experiments/2026-10-03-faithful-v48/notes.md`).
3. **Failure taxonomy of a thinking-off 31B agent, measured from traces** (`scripts/faithful_metrics.py`):
   - verbatim loops at temperature 0.2 (up to 23 identical calls), gone at 0.7;
   - the model writes no text before tool calls (0 of ~1,900 steps), so it has no scratchpad and cycles;
   - re-searching guessed names after empty results (up to 19 times in one task);
   - paging through files 60 lines at a time (up to 21 consecutive reads);
   - malformed calls (a stray backtick swallows `old_string`) resent ~30 times; rejected calls do not count toward
     `max_tool_calls`, so the loop runs to the session timeout;
   - plumbing before behaviour (signatures/docstrings edited, core logic never reached);
   - fixing one method but not its identical sibling (`append` vs `append_text`);
   - hidden-test infinite loops exhausting host memory during verification (our OOM kills).
4. **Negative result:** asking the thinking-off model for a one-line note before each call makes it emit empty
   thought-channel markers instead (`<|channel>thought <channel|>`), with no tool call: 7/16 vs 8/16
   (`experiments/2026-10-03-faithful-v49/notes.md`).
5. **Prompt progression on the 16-task faithful holdout:** v4.5 7 -> v4.6 8 -> v4.7 8 -> v4.8 8 -> v4.9 7 -> v5.0n 9,
   with v5.0n keeping every earlier solve, adding a never-solved task, and having the fewest repeats, timeouts and
   minutes (`experiments/2026-10-04-faithful-v50n/notes.md`).
6. **The public leaderboard cannot resolve scaffold tweaks.** Every LB value is k/58 truncated, so the public half
   is 58 tasks. Eight scored days of different configs all land in 4-6 tasks (mean 4.9, sd 1.0; a single run's
   binomial sd at this rate is ~2.1). Offline gains of +1/16 are below LB resolution; final selection should pool
   evidence rather than chase single-day scores.
7. **Provided code-intelligence tools are rarely usable:** only 69 of 256 public snapshots have both a non-empty
   graph and embeddings, the harness advertises the tools per repo, and the model never calls them.
8. **Context, not turns, binds:** ADK events compaction never fires inside a task; a context-budget prompt section
   moved overflow from 12/33 to 2/33 tasks on the proxy.

## Method
- Official harness (wheelhouse swegemma 0.2.7 / adk-submission 0.2.11 / google-adk 1.36.1), faithful sandbox patch,
  holdout split `experiments/splits.json` (seed 20260924), 16-task subset (fastapi 8, requests 4, rich 4).
- Every faithful run: `task_results.jsonl`, `summary.json`, `run.log`, `notes.md` under `experiments/`.
- Every daily Kaggle submission logged with its config snapshot and error text.

## Tables to produce
| table | source |
|---|---|
| faithful-eval metrics by prompt version (solved, no-edit, repeats, dead-term repeats, paging, timeouts, minutes) | `scripts/faithful_metrics.py` over the v4.5-v5.0n results |
| LB by day: config, budget, tasks solved, runtime, error text | `experiments/kaggle_submissions.md` |
| failure taxonomy: occurrences per run | trace scripts in `scripts/` |
| GPU hours per decision | `experiments/kaggle_gpu_hours.md` |

## Open items
- Whether a step change (LoRA on self-generated 31B trajectories, or thinking on) moves the LB beyond noise.
- Add day 14+ LB results to the pooled noise estimate.
