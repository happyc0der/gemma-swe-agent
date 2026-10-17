# Faithful eval: v5.6 on set AB (all 33 holdout tasks), kernel v17

Kernel v17, 10-16 13:06 UTC to 17:37 UTC (4.52 GPU h, ALL_DONE). Harness swegemma 0.2.11 / adk_submission 0.2.13
(wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed (fastapi_14303 solved, median 36 tokens/step), 4 GB
`ulimit -v` cap on sandbox commands. Raw results: `data/faithful_results/v56-AB/`.

v5.6 = v5.0n with edit_file removed: every change to an existing file goes through one run_command heredoc
`/tmp/fix.py` (OLD/NEW raw strings, assert count == 1).

## Result vs v5.0n (new harness: v13 set A + v12 set B)

| | v5.0n | v5.6 (v17) |
|---|---|---|
| solved, 33 tasks | 13/33 | **11/33** |
| changed tasks | fastapi_12942, fastapi_14485, rich_3777 solved | fastapi_15589 solved |
| no-edit tasks | 4 | 4 |
| exact repeat calls | 184 of 1061 (17%) | **92 of 961 (9.6%)** |
| "mandatory input parameters are not present" (malformed calls) | 81 hits in 6 tasks | **0** |
| paging >= 4 reads | 11 tasks | 5 tasks |
| `submit_patch` typed as a shell command (run_command) | 0 | **24 calls in 17 tasks** |
| session timeouts | 4 | 4 (fastapi_12942, rich_3052, rich_3278, rich_3061) |
| median first edit (call #) | 17 / 24 | 20 |
| median output tokens/step | 34-36 | 36 |

**Decision: 2 tasks short of v5.0n on the 33-task holdout; v5.0n stays the submission (ship rule).**

## What happened
- The fix-script route worked as intended: no malformed calls at all, exact repeats halved, and the tasks v5.0n lost
  to edit_file loops did not loop (rich_3061, rich_3278 and fastapi_14482 still failed, for other reasons).
- Lost tasks: fastapi_14485 got a plausible but wrong fix (evaluated ForwardRef in get_typed_annotation, submitted
  at call 15, then spent the rest grepping tests); rich_3777 implemented TTY_INTERACTIVE so that "1" did not force
  interactive (hidden test fails on `assert console.is_interactive`); fastapi_12942 wrote 12+ repro scripts that
  all passed and timed out without an edit (the known "cannot reproduce" mode). These look like ordinary
  sampling misses rather than something v5.6 caused.
- New waste: with only run_command left for editing, the model also sends `submit_patch` to the shell
  (`/bin/bash: submit_patch: command not found`) in 17 of 33 tasks, 24 calls in all, often 2-3 times in a row
  near the end of the budget (rich_3777: calls 26, 31, 35). v5.0n and v5.4 traces have 0 and 1 such calls.
- Infra: llama-server was OOM-killed twice (16:57, 17:04), both during rich_3480 (16:54-17:03), even with the 4 GB
  cap. Host RAM stayed at ~28.6 GB used for the rest of the run, and the three rich tasks after it (rich_3052,
  rich_3278, rich_3061) all hit the session timeout. Leftover processes from rich_3480 may have slowed those
  tasks. v5.0n lost rich_3278 to a timeout too, and none of these three counts toward the 2-task gap.

## Next (v5.7)
v5.7 = v5.6 + one static sentence in the tool description: submit_patch is a tool call with no arguments, never
a shell command. Kernel v18 runs it on AB.
