# Faithful eval: prompt v4.5, real 31B, 16 holdout tasks: 7/16

Kernel `dankaxon/gemma4-faithful-eval` v1 (T4x2, 2.8 h): official Evaluator, scorer-like sandbox, llama.cpp with
thinking off (verified: no reasoning text), v4.5 at 3.5 min x3 = 10.5 min, 40 calls, temperature 0.2.
requests 4/4, fastapi 3/8, rich 0/4. llama-server was OOM-killed 5 times (restarted in ~90 s; LiteLLM retries
carried the in-flight tasks, no task errored on a dropped connection).

| failure mode | evidence | v4.6 change |
|---|---|---|
| verbatim loops at temperature 0.2 | fastapi_14301: one command 23 times in a row; rich_3278: 19 in a row; rich_3061 22, rich_3480 17 exact duplicates | temperature 0.7 (the 12B showed the same low-temperature loops); stronger no-repeat rule |
| rewriting repros instead of fixing | fastapi_14246: the bug never reproduced ("Test passed!"), 6+ new 55-line scripts, no edit | repro under 20 lines; after two attempts that don't show the bug, implement the change the issue describes |
| editing too late or never | solved tasks: first edit at call 4-12 (one at 23); unsolved: 32-40 or never (5 of 9) | if no source edit by call 10, make the best edit now |

Per-task results in `task_results.jsonl`; full logs and traces in the kernel output.
