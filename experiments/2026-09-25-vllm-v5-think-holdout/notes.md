# MSI vLLM proxy: prompt v5 (no write_file for scratch, mandatory git-status cleanup, live-file check), day-3 budget (5.5 min / 30 calls), thinking on

Result: **4/33** vs 7/33 for v4 under the identical budget. Scratch/test-file leaks: **0 of 10** non-empty patches (v4: 9 of 15). Explicit submits 12 (v4: 11), mean 276 s, median 22 calls.
Taxonomy: budget 16 (v4: 10), broke_tests 5, no_patch 4, context_overflow 3, loop 1. Lost fastapi_13537, rich_3777, rich_3894; solved nothing new.
Reading: the hygiene rules work exactly as intended, but the added checklist steps (git status, cleanup, live-file check) consume calls and minutes that the 5.5-minute budget does not have, so fewer patches get finished. At a larger budget the trade-off may flip. Decision (rule set in advance): day 3 ships v4, plus only the single-sentence write_file warning, which adds no steps.
