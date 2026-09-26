# Day 4 (2026-09-27 00:05 UTC): prompt v4.2, thinking off, 5.5 min / 30 calls / 60 turns, timeout 180 s

## What changed since day 3 and why

The organizers published the real harness on 2026-09-25 (Kaggle dataset
`metric/gemma-4-developer-agent-wheelhouse`: swegemma 0.2.7, adk-submission 0.2.11,
adk-eval-core 0.1.0, google-adk 1.36.1, vllm 0.19.1). Source unpacked in `harness/official/`.
Running our day-3 submission through it (MSI, 12B proxy, `~/off_eval.sh`) showed the systematic
failure that our own harness never reproduced:

- **Every `read_file` call with a line range fails** with
  `'>' not supported between instances of 'int' and 'str'`. Cause (verified with a probe on the MSI
  against one vLLM server, `/tmp/adk_probe.py`): google-adk 1.36.1 serializes `int | None`
  parameters as `{"any_of": [{"type": "INTEGER"}, {"type": "NULL"}], "nullable": true}` in the
  OpenAI tools payload; the Gemma 4 template renders that, the model emits the numbers as quoted
  strings, vLLM keeps them as strings, and neither ADK nor swegemma coerces. ADK 2.9.2 (our proxy
  harness) sends `anyOf`/`integer` and the same model then emits integers, which is why swelite
  never showed the failure. In the first two official-harness
  tasks 20 of 24 read_file calls errored. Our prompt v4/v4.1 told the model to read in 80-line
  ranges, so the agent burned its calls on errors. Same mechanism hits `allow_multiple`
  (a string "false" is truthy), `k`, `max_neighbors` and the list argument of `get_code_subgraph`.
- Prompt v4.2 therefore says: tool arguments are strings only; read regions with
  `sed -n 'A,Bp' path` via run_command; read_file only with the path; edit_file with exactly
  three arguments; don't use get_code_subgraph.
- `include_thoughts: false` maps to `enable_thinking: false` (adk_submission
  `apply_thinking_config_to_model`); `thinking_level` maps to vLLM `reasoning_effort` only when
  thinking is on. Dropped thinking_level; kept thinking off (day-3 was already off).
- `timeout_seconds` is also the pytest timeout of the hidden-test verification
  (`swegemma/harness/verification.py`), so 120 s could fail a correct patch; now 180 s.
- max_output_tokens 2048 -> 4096 (thinking is off, so this only matters for long edits).
- Organizer answers (discussion 743063): tasks run sequentially; the scorer reads only the four
  eval_config fields; default is no limit; hitting 12 h currently errors the submission.

## Evidence
- Real 31B (Kaggle T4x2, llama.cpp, our harness, day-3 config): 3/33 holdout, 192 min,
  `experiments/2026-09-26-kaggle-31b-v8/`.
- Official harness, 12B proxy, v4.1: `off-v41-holdout-partial` (2 tasks, 0 solved, 20/24
  read_file errors); full v4.2 vs v4.1 vs sample-noadapter runs queued on the MSI.

## Run hygiene note
- `off-v42-holdout` task `requests_7427` failed with a Docker 404: I removed "stale" containers while the
  run was live and hit its sandbox. Treat that task as a sandbox error, not a model failure; never prune
  containers while an official-harness run is in progress (each task creates and removes its own).

## Official harness, 12B proxy, holdout 33 (concurrency 1, shared GPU)
| run | resolved | patches | read_file calls / errors | edit errors | submit calls | ended by |
|---|---|---|---|---|---|---|
| v4.2 (`off-v42-holdout`, 06:51 UTC) | **4/33** (requests_7309, rich_4075, rich_3052, rich_3061) | 11 | 283 / 180 | 25 | 18 in 9 logs | 14 call-budget, 5 context overflow, 3 time, 1 sandbox (my pruning), 10 clean |

Even with the prompt telling it not to, the 12B kept calling read_file with ranges (64 % of those calls
failed), which is why v4.3 removes the tool altogether. Per-task results: `off-v42-holdout.task_results.jsonl`.
