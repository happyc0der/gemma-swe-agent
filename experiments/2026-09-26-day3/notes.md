# Day 3: prompt v4, temp 0.7, thinking low/512 (include_thoughts false), 2048 cap, 5.5 min / 30 calls / 60 turns, command timeout 120 s

Why: days 1 and 2 scored 0.00 with 8 and 10 min/task while the same day-2 config resolved 6/33 on the proxy. The organizers' sample uses 1 min/task, so a sequential 12 h run is plausible; on 4x L4 with the 31B and thinking, per-call latency is several times the proxy's. 5.5 min x 120 = 11 h worst case.

Local test of this exact config (MSI vLLM 12B proxy, 33 holdout): **5/33** vs 7/33 for the same prompt at 10 min / 50 calls. Lost fastapi_13537 (needed 407 s) and requests_6644 (needed 50 calls). But the run is well-behaved: 24/33 called submit_patch explicitly, only 2 context overflows (was 12), 17 non-empty patches, mean 185 s/task (120 tasks sequential ~6.2 h even before the cap bites), taxonomy broke_tests 11 / loop 6 / no_patch 5 / budget 2.

Decision: ship this config for day 3 (armed for 2026-09-26 00:05 UTC). If day 3 also scores 0.00, the cause is not budget; next suspects are compile-time incompatibility with the organizers' stack and the hidden repos' difficulty, and I need the submission page's log (asked Keshav).

## Preview with thinking ON (reasoning_effort=high, include_thoughts false), same 5.5 min / 30 calls
**7/33** (the thinking-off preview of this config gave 5/33; the best 10-min runs gave 7/33). With thoughts excluded from history the overflow penalty seen in the 10-min thinking run mostly disappears. This is the closest local approximation of what day 3 does if the organizers' stack enables thinking; it is the strongest local result at the short budget, so the staged config stands.
