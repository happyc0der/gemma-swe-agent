# Kernel v29: pub-budget-fit-off on set AB again = 12/33 (identical rerun of v23 = 9/33)

Pushed 2026-10-29 02:50 UTC, ran 02:52-07:00 (4.13 GPU h; RUN_DONE 212 min). Same files, same harness, same
pinned llama.cpp, same 33 tasks as kernel v23 (experiments/2026-10-21-faithful-bf-off-AB). Archive:
data/faithful_results/bf-off-AB-rerun (results/faithful-pub-budget-fit-off-setAB, run.log, llama logs).

| run | resolved | no-edit tasks | exact repeats | session timeouts | median first edit | agent min |
|---|---|---|---|---|---|---|
| pub-budget-fit-off v23 (10-21) | 9 | 6 | 281 / 818 | 1 | 20 | 220 |
| pub-budget-fit-off v29 (10-29, identical) | **12** | 4 | 217 / 807 | 2 | 17 | 212 |
| bf-nomatch-off v26 | 11 | 6 | 282 / 850 | 0 | 17 | 167 |
| bf-noedit-off v28 | 8 | 28 | 202 / 826 | 1 | 99 | 222 |

- Per task: v29 solves all 9 of v23's tasks plus fastapi_14360, fastapi_5624 and requests_7427. 30 of 33 tasks agree;
  the 3 that flip are the ones a candidate "gains" or "loses".
- So one 33-task thinking-off run moves by about 3 tasks with identical files. Pooled base = 21/66 (10.5 per 33).
  bf-nomatch's screen (11/33) is +0.5 over the pooled base, not +2; bf-noedit (8) and bf-editfb (7) are about 1 SD
  below it, and bf-warn (10) is level with it. None of the four screens separates from noise on its own.
- The one effect that held against both base runs is time: bf-nomatch's agent time 167 min vs 220 / 212 (-22%).
- Consequence for screening: a single 33-task paired run can only rule out large regressions (>= 4 tasks). Small
  edits need more tasks (the 74 stable dev tasks are unused since the switch to the public base) or LB days.

Next: kernel v30 runs pub-budget-fit-off and bf-nomatch-off on 33 stable dev tasks (subset "DEV": fastapi 19,
rich 12, requests 1, httpx 1), a third independent paired set, to firm up the bf-nomatch decision while its LB days run.
