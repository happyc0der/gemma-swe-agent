# Faithful eval: v5.8 on set AB (all 33 holdout tasks), kernel v19

Kernel v19, pushed 10-18 13:15 UTC, started 17:04 UTC (queued 3.8 h), ALL_DONE 21:28 UTC (4.39 GPU h). Harness
swegemma 0.2.11 / adk_submission 0.2.13 (wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed
(fastapi_14303 solved, median 35 tokens/step), 4 GB `ulimit -v` cap on sandbox commands. Raw results:
`data/faithful_results/v58-AB/`.

v5.8 = v5.7 (v5.0n without edit_file; edits via one run_command fix script; submit_patch is a tool) + a
budget-warning protocol: when a tool result carries `budget_warning` (the harness adds it once 10 calls remain),
exploration is over; if nothing is edited yet, the very next call is the fix script, then one run, then submit_patch.

## Result vs v5.0n (new harness: v13 set A + v12 set B) and v5.7

| | v5.0n | v5.7 (v18) | v5.8 (v19) |
|---|---|---|---|
| solved, 33 tasks | 13/33 | 12/33 | **14/33** |
| gained vs v5.0n | | fastapi_14791, rich_3278 | fastapi_15589, **fastapi_5624 (first solve by any variant)** |
| lost vs v5.0n | | fastapi_14458, fastapi_14485, rich_3777 | requests_7205 (repro spiral, timed out before any edit) |
| no-edit tasks | 4 | 3 | 3 (fastapi_14099, requests_7205, rich_3938) |
| exact repeat calls | 184 of 1061 (17%) | 104 of 873 (12%) | 128 of 935 (14%) |
| repeat searches of a dead term | 38 | 43 | 17 |
| malformed calls | 81 in 6 tasks | 3 in 1 task | 3 in 1 task (requests_7309) |
| `submit_patch` typed as a shell command | 0 (had edit_file) | 8 calls in 8 tasks | 6 calls in 6 tasks (one each) |
| session timeouts | 4 | 4 | 5 (fastapi_14099, 14448, 14583, requests_7205, rich_3061) |
| median first edit (call #) | 17 / 24 | 17 | 15 |
| median output tokens/step | 34-36 | 35 | 35 |
| agent time | | 215 min | 228 min |

**Decision: ships. 14/33 is the first result above v5.0n's 13/33 in six 33-task runs; it is better on every
wasted-call metric except one extra session timeout, and its only loss against v5.0n is a failure mode v5.0n
shows itself (rich_3278 in v13: 34 dead repeats of a reproduction). +1 task is inside the coin-flip band (10 of the
33 tasks flip between runs), so this is a marginal call; the LB days from 10-20 on are the check, and reverting
means pointing `.submit_fallback` back at v50n-t45.**

## What happened
- The warning protocol is obeyed about a third of the time. 18 tasks reached the warning (first warned result at
  call 30, so call 31 is the first "warned" call). The call after it was the fix script in 4 tasks (fastapi_5624
  -> solved, rich_3278, rich_3480, rich_3535), a repro/test run in 2 (fastapi_12942 and rich_3777 -> both solved),
  and grep/sed/a new repro script in 12. Of the 10 tasks that had not edited by call 30, 3 edited at call 31, 2
  at 32, 3 at 36-38 and 2 never (v5.7: 12 such tasks, 9 edited at 32-36). fastapi_5624 is the one solve the
  protocol can claim directly: edit at call 31, one test run, submit.
- requests_7205 (solved in every earlier run at calls 6-9) rewrote /tmp/repro.py 15 times (300-470 tokens each,
  ~35 s each on the T4) fighting the stdlib netrc parser's "bad toplevel token" and ran out of time at 25 calls
  without an edit. The warning never fired, so the protocol could not help; this is the known repro-spiral mode.
- **New finding: silent no-op fix scripts.** 28 of the 70 fix scripts in this run contain no write call at all
  (v5.7: 10 of 44, v5.6: 17 of 54), and 41 of 70 contain comment lines: the model reasons inside the heredoc
  (`# Wait, I should use the exact OLD block from the file.`) and stops before the assert/replace/write line. The
  script exits 0 with empty stdout, which looks like success. rich_3278 ran the same no-op script 12 times
  (calls 16-33), each followed by a `sed -n` that showed the file unchanged, then tried `sed -i`, broke the file,
  `git checkout`ed it and submitted an empty patch. fastapi_13713 and rich_3535 lost 3 calls each the same way,
  fastapi_14448 and rich_3061 2 each. The prompt's `print('ok')` is the only success signal and the model does
  not notice its absence.
- Unsolved 19: 6 with no patch (fastapi_14099 T, fastapi_14246, requests_7205 T, rich_3278, rich_3938, rich_4075),
  3 timeouts with a patch (fastapi_14448, fastapi_14583, rich_3061), 3 patches that crash in the hidden tests
  (AttributeError in fastapi_13713 and fastapi_14482, UnboundLocalError in fastapi_14964), the rest fail
  assertions (wrong semantics). No SyntaxError this run.
- Across the six 33-task runs (v5.0n, v5.4, v5.6, v5.7, v5.8 plus the partial v5.3/v5.5): 8 tasks solved every
  time, **15 never solved by any variant** (fastapi_5624 left that group today).
- Infra: llama-server was OOM-killed once (20:56 UTC, during rich_3480 again), restarted by the watchdog in 90 s;
  the run completed. The kernel waited 3.8 h in Kaggle's queue before starting.

## Next (v5.9)
v5.9 = v5.8 with the fix-script template reshaped so that a half-written script fails loudly instead of
succeeding silently: a two-line `edit(p, old, new)` helper (count, assert, write, print) followed by one
`edit('pkg/module.py', r'''old''', r'''new''')` call per change; no comments or other statements inside the
script; the prompt states that only an `ok` line means the file changed. An unfinished call is a SyntaxError
(non-zero exit) rather than an exit-0 no-op. Kernel v20 runs it on AB.
