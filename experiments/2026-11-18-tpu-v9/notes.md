# TPU v9 (2026-11-18): bf-pin thinking on, paired with the base

Kernel dankaxon/gemma4-tpu-eval v9, pushed 11-16 ~14:25 UTC (commit 76ef58f), collected 11-18 14:00 UTC into
data/tpu_results/v9 (6.25 TPU h by quota; weights in /dev/shm, 52 s download, decode 64.0 tok/s, time_scale 0.52,
verdict "stage 2 rc=0"). Thinking-on, vLLM on TPU v5e-8, official Evaluator, 33-task subsets.

| run | resolved | agent time | steps | median / p90 output tokens |
|---|---|---|---|---|
| bf-pin AB | **15/33** | 115 min | 923 | 94 / 582 |
| bf-pin DEV | **14/33** | 126 min | 926 | 116 / 591 |
| pub-budget-fit (base) AB | 13/33 | 115 min | 866 | 93 / 512 |
| base DEV | skipped (session budget, after 6.24 h) | | | |

Earlier thinking-on base runs: AB 13 (v6), 13 (v7), 13 (v8); DEV 13 (v7), 15 (v8). With v9 the base pools to
AB 13, 13, 13, 13 and DEV 13, 15 (80/198 = 13.3 per run); bf-pin = 29/66 (14.5 per run).

Verdict: bf-pin stays pulled. The rule set on 11-16 was to reopen it only if it beat the base by >= 3 tasks on both
sets thinking on; it is +2 on AB and level on DEV (14 vs 13 and 15). Thinking on, it did not cost agent time
(115 vs 115 min on AB), unlike the thinking-off screen (+43%, T4 v34), but one 33-task run moves by ~3 tasks with
identical files, the lane overstated bf-lean (31/66 offline, 8 on the LB) and bf-t10, and there is no LB slot to
spare before the 11-26 candidate freeze without taking draws from bf-think1k, the only finals contender. Recorded
for the paper and the record only.
