# MSI vLLM proxy: prompt v4 with thinking ON (reasoning_effort=high via --llm-kwarg, include_thoughts true), 4096 cap, temp 0.7, 10 min / 50 calls

Result: **7/33 (21.2%)**, equal to thinking-off v4, with two newly solved tasks (fastapi_5624, requests_7205) and two lost (requests_6644, rich_3894). Union over all five proxy runs: 10/33.
Profile: identical repeats 1.8/task (was 8.6), median 24 calls (was 43), mean 355 s (was 207), non-empty patches 11 (was 15), explicit submits 5 (was 24+).
Taxonomy: context_overflow 18 + overflow_loop 1, budget 5, broke_tests 2. Thoughts are returned (include_thoughts true) and therefore re-sent as history, so the 32k window fills faster; most tasks died before submit_patch.
Reading: thinking removes the retry loops and improves reasoning quality per step, but with thoughts kept in history it trades loops for overflow. The right combination is thinking with a small budget and `include_thoughts: false`, which is what day 3 ships. Next preview: the exact day-3 config with thinking on.
