# Day 3: prompt v4, temp 0.7, thinking low/512 (include_thoughts false), 2048 cap, 5.5 min / 30 calls / 60 turns, command timeout 120 s

Why: days 1 and 2 scored 0.00 with 8 and 10 min/task while the same day-2 config resolved 6/33 on the proxy. The organizers' sample uses 1 min/task, so a sequential 12 h run is plausible; on 4x L4 with the 31B and thinking, per-call latency is several times the proxy's. 5.5 min x 120 = 11 h worst case.

Local test of this exact config (MSI vLLM 12B proxy, 33 holdout): **5/33** vs 7/33 for the same prompt at 10 min / 50 calls. Lost fastapi_13537 (needed 407 s) and requests_6644 (needed 50 calls). But the run is well-behaved: 24/33 called submit_patch explicitly, only 2 context overflows (was 12), 17 non-empty patches, mean 185 s/task (120 tasks sequential ~6.2 h even before the cap bites), taxonomy broke_tests 11 / loop 6 / no_patch 5 / budget 2.

Decision: ship this config for day 3 (armed for 2026-09-26 00:05 UTC). If day 3 also scores 0.00, the cause is not budget; next suspects are compile-time incompatibility with the organizers' stack and the hidden repos' difficulty, and I need the submission page's log (asked Keshav).

## Preview with thinking ON (reasoning_effort=high, include_thoughts false), same 5.5 min / 30 calls
**7/33** (the thinking-off preview of this config gave 5/33; the best 10-min runs gave 7/33). With thoughts excluded from history the overflow penalty seen in the 10-min thinking run mostly disappears. This is the closest local approximation of what day 3 does if the organizers' stack enables thinking; it is the strongest local result at the short budget, so the staged config stands.

## Scratch-file leaks (found 2026-09-25 08:00 UTC)
Across the proxy runs, 2-9 of the 10-17 non-empty patches per run contain scratch files (`tmp/repro.py`, `fix.py`, `stdout.txt`, a stray test file), and in the day-3 thinking-on run 9/15 did, 3 of them containing nothing else. Cause: `write_file("/tmp/x")` resolves to `/workspace/tmp/x` (README semantics, same in the official harness) and the pre-submit cleanup is skipped. Four of the seven "broke_tests" patches in that run are this. One more edited the wrong sibling module (`_compat/v1.py` vs `v2.py`).
Prompt v5 (queued after the dev run): forbid write_file for scratch, mandatory `git status --short` cleanup before submit, a "live file" check, and no edits under tests/. If v5 >= v4 on the holdout before 23:30 UTC, day 3 ships v5.

## v4.1 (v4 + one-line write_file warning) holdout run, 2026-09-25: aborted twice
First attempt died at 08:08 EDT with every other process on the MSI (no error; Task Scheduler stops tasks on battery by default; settings fixed). Second attempt ran while Keshav was using the laptop's GPU (Battle.net, a Windows Python process): vLLM fell to 2-14 tok/s and 13/13 tasks timed out with 2-18 calls, so it was stopped as invalid. The MSI is released to Keshav; the run will be repeated when the GPU is free. Day 3 ships v4.1 unmeasured: the only change versus the measured v4 (7/33) is one warning sentence.

## Throughput lens (2026-09-25 evening, from the first real-31B tasks on Kaggle T4x2)
The 31B via llama.cpp with two slots ran 6-8 tok/s per slot: two tasks made 6 tool calls each in ~250 s. On the 12B proxy at ~34 tok/s, the tasks v4 solved needed 6-34 calls and 72-407 s. If the competition's 4x L4 vLLM stream is only ~1.5x slower than the proxy, 5.5 min is enough for the easy half of those; if their concurrency makes it 4x slower, a 5.5-min task yields ~6 calls and nearly nothing resolves. Both prior budgets (8, 10 min) scored 0.00, so day 3 tests the short budget; day 4 should test the opposite (20+ min, few tasks may hit the global cap) unless the real-31B holdout run says otherwise.

## v4.1 (the shipped day-3 prompt) measured after the fact, thinking on, 5.5 min / 30 calls: 4/33
Same config minus the one warning sentence gave 7/33 the day before; the thinking-off variant gave 5/33. Read as run-to-run noise of about +/-3 on this 33-task holdout rather than an effect of the sentence. Leak counts compared in the analysis above.
