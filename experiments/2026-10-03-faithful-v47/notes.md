# Faithful eval: prompt v4.7 vs v4.6 vs v4.5 (same 16 holdout tasks)

| metric | v4.5 | v4.6 | v4.7 |
|---|---|---|---|
| solved | 7 | 8 | 8 |
| tasks with no edit | 5 | 3 | **1** |
| commands that hung into the 180 s timeout | 1 | 2 | **0** (15 commands timeout-wrapped) |
| exact duplicate calls | 142 | 57 | 77 |
| total calls | 491 | 441 | 498 |

Across the three runs: 6 tasks always solved, 3 borderline (fastapi_14301, rich_3278, requests_7427 flip between
runs), 7 never solved (mostly multi-file features: fastapi_12942, 13713, 14099, 14246, rich_3052, 3061, 3480).

New failure mode found in v4.7 (fastapi_12942): the model guessed a function name (`get_route_params`) and searched
for it ~20 times with different paths and flags. grep exits 1 when nothing matches, so the tool reports an error
with empty output, which the model reads as a failed command rather than "not found". Across runs: 29-53 empty
greps per run; 13-33 extra calls spent re-searching terms that had already come back empty, in 3-5 tasks per run.
Prompt v4.8 = v4.7 + "empty grep (exit 1) means not found; never re-search it; never guess names".

Memory: with --cache-ram 0 and mmap the server was killed once (was 3-5 times).
