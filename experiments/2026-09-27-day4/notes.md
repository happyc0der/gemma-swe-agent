# Day 4 (2026-09-27 00:05 UTC): prompt v4.3, thinking off, 5.5 min / 30 calls / 60 turns, timeout 180 s

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
| v4.1 (`off-v41-holdout`, 07:50 UTC) | **5/33** (requests_7309, rich_4075, rich_3942, rich_3052, rich_3061) | 5 | 497 / 381 | 5 | 18 in 9 logs | 21 call-budget, 2 overflow, 1 time, 9 clean |
| v4.3 (`off-v43-holdout`, 08:45 UTC) | **5/33** (requests_7427, requests_7309, rich_3942, rich_3480, rich_3061) | 12 | 0 / 0 (tool removed; 917 run_command) | 23 | 34 | 9 call-budget, 3 overflow, 4 time, **17 clean** |
| v4.3 + read-only `code_analyzer` AgentTool (`off-v43-analyzer-holdout`, 10:20 UTC) | **5/33** (requests_7427, rich_4075, rich_3942, rich_3894, rich_3061) | 8 | 0 / 0 (301 run_command, 68 analyzer calls) | 12 | 30 | 17 call-budget, 1 time, 15 clean, 0 overflow |
| organizers' sample prompt, no adapters, thinking off (`off-sample-noadapter-holdout`, 08:51 UTC) | **2/33** (requests_7309, rich_3052) | 5 | 214 / 240 (incl. errors on other tools) | 36 | 12 | 24 call-budget, 2 time, 6 clean |

Reading: on the 12B proxy the four configs are within the +/-3 noise band (2-5/33), so the read_file
failure is not what separates 5/33 from 0.00 on the scorer; the 31B + vLLM 0.19.1 path still has an
unexplained difference (see the day-3 score once it lands, and the planned vLLM 0.19.1 + real-31B run on the
MSI). v4.3 stays the day-4 choice because it wastes no calls on rejected arguments (0 read errors, 17 clean
endings and 34 submit calls vs 9/18 for v4.1) and its union of solved tasks differs (requests_7427, rich_3480).
Per-task results for every run: `off-*-holdout.task_results.jsonl` in this folder.

Even with the prompt telling it not to, the 12B kept calling read_file with ranges (64 % of those calls
failed), which is why v4.3 removes the tool altogether. Per-task results: `off-v42-holdout.task_results.jsonl`.


## CORRECTION (14:10 UTC 2026-09-26): the read_file failure does NOT happen on the scorer's stack

I built a scorer replica on the MSI: the wheelhouse's exact vLLM 0.19.1 / transformers 5.13.1 /
compressed-tensors 0.15.0.1 serving the real `gemma-4-31B-it-qat-w4a16-ct` (CPU offload 11.5 GB, eager,
no LoRA buffers, one patched offload guard; ~0.5 tok/s), driven by google-adk 1.36.1 from the wheelhouse
(`v019_probe.py`, log `v019_31b_probe.log`). The server returned `"start_line": 300` as a JSON integer
and the tool function received the integer 300 (the log prints `repr()` values, so `'300'` there is the
int). A mocked-response test (`trace_args.py`) confirms neither ADK 1.36.1 nor 2.9.2 turns integers into
strings.

So the string line numbers came from my proxy (12B on vLLM 0.30 with ADK 1.36.1), not from the scorer.
My earlier claim that an ADK 1.36.1 `any_of` schema bug caused the three 0.00 scores is withdrawn; the
schema serialization difference is real, but on the scorer's model and vLLM it does not break read_file.
The forum post draft is retracted. The 0.00 cause is still unknown; leading hypotheses are the 12 h
sequential cap (days 1-2 budgeted 8 and 10 min per task) and the scorer-side bundle issue the organizer
mentioned on 09-26.

Consequences: v4.3 (no read_file tool) is not a fix, only a harmless variant (5/33 on the proxy, same as
v4.1). Next: make the proxy faithful by serving the 12B on vLLM 0.19.1, confirm read_file works there,
and rerun v4.1 vs v4.3 before the 00:05 UTC submission.
- 14:15 UTC: vLLM 0.19.1 cannot load the 12B W4A16 checkpoint (`ValueError: Expected hidden_size to be 3840,
  but found: 256` in `layernorm.py`), so a faithful 12B proxy on the scorer's vLLM is not possible; the 31B on
  0.19.1 works but runs at ~0.5 tok/s with offload, too slow for holdout runs. Back on the 0.30 proxy, I am
  running v4.3 through swelite (ADK 2.9.2, where read_file works) to compare with the existing swelite v4.1
  numbers before choosing the day-4 config.
