# MSI vLLM proxy: prompt v3 at temperature 0.7 (otherwise the day-2 config), 33 holdout tasks

Result: **6/33 (18.2%)**, same total as temperature 0.2, but a different failure mix and different tasks:
- resolved: fastapi_13537, fastapi_14303, fastapi_14458, requests_7309 (both runs) + rich_3777, rich_3894 (new); lost requests_6644, fastapi_14301. Union over both runs: 8/33.
- identical repeats per task 13.5 -> 5.1; max identical run 13.2 -> 4.5; successful edits 1.0 -> 2.1; non-empty patches 10 -> 14; mean time 307 s -> 267 s.
- taxonomy: context_overflow 15 + context_overflow_loop 4 (was 11 + 7), loop 3 (was 9), broke_tests 4, no_patch 1.
- calls per task rose 30.9 -> 40.5: with loops broken the model explores more, and exploration output is what overflows the 32k window.

Reading: temperature 0.7 fixes the deterministic-retry loop; the binding constraint is now context growth. Prompt v4 (bounded outputs, ~20-call plan, 2048 output cap) is the direct response and runs next. Temperature 0.7 is kept for day 3.
