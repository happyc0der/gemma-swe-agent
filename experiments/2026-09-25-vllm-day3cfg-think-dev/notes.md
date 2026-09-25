# MSI vLLM proxy: day-3 config (prompt v4, temp 0.7, 2048 cap, 5.5 min / 30 calls) with thinking on, dev split (74 usable tasks)

Result: **15/74 (20.3%)**: fastapi 7/42, rich 7/30, requests 1/1, httpx 0/1. Consistent with 7/33 (21%) on the holdout, so the estimate is stable across 107 tasks.
Taxonomy: budget 22 (5.5-min cap while still working), broke_tests 12, no_patch 10, context_overflow 9 (+1 with loop), edit_mismatch 3, loop 2. Mean 280 s/task, 27 non-empty patches, 32 explicit submits.
Scratch/test-file leaks: 12 of the 27 non-empty patches contain scratch files or test edits (5 contain nothing else); 8 of those 12 are unresolved. Prompt v5 targets exactly this and is being measured on the holdout now.
