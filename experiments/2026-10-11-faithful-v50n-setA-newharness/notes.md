# Faithful eval: v5.0n on set A under the new harness (baseline for the daily routine)

Kernel v13, 10-11 14:38-17:30 UTC (2.9 GPU h). Harness swegemma 0.2.11 / adk_submission 0.2.13 (wheelhouse of
2026-10-09), llama.cpp pinned to 71ad0590f, canary passed (fastapi_14303 solved, median 36 output tokens/step),
thinking off (`thinking_level: none`). Raw results: `data/faithful_results/v50n-setA-newharness/`.

| | v5.0n, old harness (10-04, v6) | v5.0n, new harness (10-11, v13) |
|---|---|---|
| set A solved | 9/16 | **9/16** (the same 9 tasks) |
| session timeouts | 1 | 2 (fastapi_14099, rich_3278) |
| no-edit tasks | - | 2 (fastapi_14099, fastapi_14246) |
| exact repeat calls | - | 77 of 477 |
| median first edit | - | call 17 |
| median output tokens/step | - | 36 |
| agent time | 112 min | 137 min |

Solved: fastapi_12942, 13537, 14301, 14303, 14360; requests_6644, 7205, 7309, 7427. All four rich tasks fail.

**Ship-rule baseline (new harness, 33 stable holdout tasks): v5.0n = set A 9/16 + set B 4/17 (kernel v12) = 13/33.**
A candidate must solve >= 13/33 on subset AB and beat v5.0n on the combined evidence.

Unsolved: fastapi_14099 (39 calls, no edit, timeout), fastapi_14246 (37 calls, no edit), fastapi_13713 (edit at 31,
wrong), rich_3480 (sibling method missed; v5.1's sibling rule solved it once), rich_3052, rich_3061, rich_3278
(timeout, empty patch).
