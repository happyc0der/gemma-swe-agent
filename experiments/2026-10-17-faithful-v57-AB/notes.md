# Faithful eval: v5.7 on set AB (all 33 holdout tasks), kernel v18

Kernel v18, 10-17 13:14 UTC to 17:29 UTC (4.25 GPU h, ALL_DONE). Harness swegemma 0.2.11 / adk_submission 0.2.13
(wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed (fastapi_14303 solved, median 39 tokens/step), 4 GB
`ulimit -v` cap on sandbox commands. Raw results: `data/faithful_results/v57-AB/`.

v5.7 = v5.6 (v5.0n without edit_file; edits via one run_command fix script) + one static sentence: submit_patch is a
tool call with no arguments, never a shell command.

## Result vs v5.0n (new harness: v13 set A + v12 set B) and v5.6

| | v5.0n | v5.6 (v17) | v5.7 (v18) |
|---|---|---|---|
| solved, 33 tasks | 13/33 | 11/33 | **12/33** |
| gained vs v5.0n | | fastapi_15589 | fastapi_14791, rich_3278 (never solved before) |
| lost vs v5.0n | | fastapi_12942, fastapi_14485, rich_3777 | fastapi_14458, fastapi_14485, rich_3777 |
| no-edit tasks | 4 | 4 | 3 |
| exact repeat calls | 184 of 1061 (17%) | 92 of 961 (9.6%) | 104 of 873 (12%), 35 of them one grep in fastapi_14485 |
| malformed calls | 81 in 6 tasks | 0 | 3 in 1 task |
| `submit_patch` typed as a shell command | 0 | 24 calls in 17 tasks | **8 calls in 8 tasks** (one each, then the tool) |
| tasks with an identical-call streak >= 5 | 3 | 1 | 1 (fastapi_14485, 24 in a row) |
| session timeouts | 4 | 4 | 4 (fastapi_14448, fastapi_14458, rich_3061, rich_3938) |
| median first edit (call #) | 17 / 24 | 20 | 17 |
| median output tokens/step | 34-36 | 36 | 35 |
| agent time | | 235 min | 215 min |

**Decision: 1 task short of v5.0n on the 33-task holdout; v5.0n stays the submission (ship rule).**

## What happened
- The sentence worked as far as it goes: submit_patch-in-the-shell fell from 24 calls to 8, and every remaining case
  is a single `command not found` followed by the real tool call.
- The two gains (fastapi_14791 at call 16, rich_3278 at call 23) are tasks no variant had solved before. The three
  losses are coin-flip tasks: fastapi_14485 looped on one empty grep (`grep -rn "get_type_hints" fastapi/`) 35
  times despite the prompt's own rule against it; fastapi_14458 edited twice but its repro never changed and it
  timed out; rich_3777 implemented TTY_INTERACTIVE with the same wrong semantics as in v5.6.
- Across the five 33-task runs under the new harness (v5.0n, v5.3, v5.5, v5.6, v5.7): 8 tasks are solved every
  time, 10 are coin flips, and **16 have never been solved by any variant**. The +-2 differences between variants
  come entirely from the coin flips.
- The never-solved 16 in this run: 4 ended with no patch (fastapi_14099, fastapi_14246, fastapi_15023, rich_3938),
  6 submitted a patch that crashes in the hidden tests (NameError `external_docs` in fastapi_13713,
  UnboundLocalError in fastapi_14964, a SyntaxError in rich_4075 from a hand-rolled `re.sub` whose replacement
  string turned `"\n"` into a real newline, AttributeError/TypeError in fastapi_14448/14482/rich_3061), and the rest
  fail assertions (wrong semantics).
- Late edits are triggered by the harness, not by the prompt: the harness appends `budget_warning` to every tool
  result once 10 calls remain (swegemma/tools/base.py, fixed threshold). In this run 12 tasks had not edited by
  call 30; 9 of them made their first edit at calls 32-36, i.e. within 2-6 calls of the first warning, and then had
  4-8 calls left (only fastapi_12942 still got solved). The prompt's own "edit by your 10th call" checkpoint is
  ignored, as before.
- Infra: llama-server was OOM-killed once (16:59, during the rich tasks), restarted by the watchdog; the run
  completed.

## Next (v5.8)
v5.8 = v5.7 + a budget-warning protocol in the working rules: when a tool result carries `budget_warning`,
searching and reading are over; if nothing is edited yet, the very next call is the fix script, then one repro or
targeted test run, then submit_patch. It anchors on the one nudge the model demonstrably obeys instead of a
self-counted checkpoint. Kernel v19 runs it on AB. Candidate after that: make the fix-script template compile the
file it wrote (`py_compile`) and forbid `re.sub` replacements (rich_4075).
