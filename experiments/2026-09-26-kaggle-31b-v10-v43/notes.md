# Kaggle T4x2, real 31B (llama.cpp Q4_0, 32k), day-4 config (v4.3, 4.5 min / 30 calls): 1/33

Kernel `dankaxon/gemma4-31b-holdout-eval` v10, queued 16:29-19:01 UTC, eval 175 min, no server restarts.
Resolved: requests_7309. 32 of 33 tasks ended on the time budget (22 between turns, 10 mid-turn); only 1
explicit submit_patch. Mean 12.1 tool calls, 288 s agent time, 318 s per task end to end (max 348 s).

Reading: on T4 (~12 tok/s) 4.5 min buys ~12 tool calls, too few to finish most tasks; 1/33 vs 2-3/33 at
5.5 min is inside the noise band. The scorer's 4x L4 with TP=4 decodes several times faster with thinking
off, so this bounds the day-4 config from below. The 4.5 min cap stays for day 4 because it keeps 120
sequential tasks at ~10.4 h worst case under the 12 h cap; if day 4 scores, day 5 can raise it.
Note the official harness keeps the working-tree diff as the patch when submit_patch is never called, so
unfinished edits still get verified on the scorer.
