# Kernel v30: pub-budget-fit-off 9/33 vs bf-nomatch-off 10/33 on 33 stable dev tasks (subset DEV)

Pushed and started 2026-10-29 11:10 UTC, finished 19:08 UTC (7.97 GPU h). Subset DEV = the first stable dev tasks by repo
quota (fastapi 19, rich 12, requests 1, httpx 1), unused since the switch to the public base, so a third independent
paired set after holdout A and B. Archive: data/faithful_results/bf-pair-DEV (results/, run.log, kernel log).

| run | resolved | no-edit tasks | exact repeats | 80-turn cap | session timeouts | agent min |
|---|---|---|---|---|---|---|
| pub-budget-fit-off | 9 | 7 | 516 / 1058 calls | 5 | 0 | 242 |
| bf-nomatch-off | 10 | 11 | 308 / 862 | 2 | 1 | 200 |

- Per task: same 9 solved by both, plus rich_2725 for bf-nomatch (the base looped to the 80-turn cap there).
- The repeat loops that run to the 80-turn cap fall from 5 tasks to 2 and exact repeats by 40%; agent time -17%.
- But no-edit tasks rise 7 -> 11 (bf-nomatch stops searching sooner and sometimes ends without an edit).

Pooled thinking-off evidence (paired tasks):

| config | AB runs | DEV runs | solved | per 33 tasks | agent min per run |
|---|---|---|---|---|---|
| pub-budget-fit-off | 9, 12 | 9 | 30 / 99 | 10.0 | 220, 212, 242 |
| bf-nomatch-off | 11 | 10 | 21 / 66 | 10.5 | 167, 200 |

Verdict so far: level on solved tasks (+0.5 per 33, inside the ~3-task run noise), consistently faster (-17% to -24%),
which matters only as 12 h runtime margin. The LB days decide (day 1 = 8; day 2 queued). Kernel v31 reruns
bf-nomatch-off on AB so both configs have the same paired design (AB x2 + DEV x1).
