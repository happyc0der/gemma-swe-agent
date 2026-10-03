# Faithful eval: prompt v4.8 vs v4.7 vs v4.6 (same 16 holdout tasks)

Kernel `dankaxon/gemma4-faithful-eval` v4, T4x2, 16:09-18:12 UTC (123 min of agent runs, 2.6 GPU h with setup).

| metric | v4.6 | v4.7 | v4.8 |
|---|---|---|---|
| solved | 8 | 8 | 8 (same set as v4.7) |
| tasks with no edit | 3 | 1 | 1 |
| commands that hung into the 180 s timeout | 2 | 0 | 1 |
| exact duplicate calls | 57 | 77 | **130** (27% of all calls) |
| repeat searches for a term that already came back empty | 18 | 33 | 24 |
| median call of first edit | 18 | 17 | 23 |
| total calls | 441 | 498 | 488 |

Verdict: no better than v4.7, so day 10 stays v4.7 at 4.5 min.

Why the v4.8 rule did not work:
- It described an empty grep wrongly. The traces show two forms. Piped through `head` (56 of 85 empty greps), the
  tool returns `{"status": "ok", "stdout": "", "exit_code": 0}`; unpiped (27), a `CommandError` with exit code 1
  and empty output. The prompt's own template pipes through `head`, so the common case looked like a successful
  command, not "not found".
- The underlying failure is broader than dead greps. With thinking off the model writes **no text at all** before
  its tool calls (0-1 text messages per task; most steps are 27-35 completion tokens, the bare call). With no
  scratchpad it cycles: 18 identical greps for a guessed name in fastapi_12942, 23 identical `python3 -c` regex
  probes in rich_3278, read-code / rerun-repro cycles in rich_3061, 5 identical `edit_file` calls in rich_3052.
  The "never run a command whose exact text you already ran" rule does not stop it once the loop starts.

Prompt v4.9 = v4.8 + a one-line note (at most 25 words) before every tool call stating what the last output showed
and what the call will do, with "if your note repeats an earlier one, you are going in circles: edit, read
something else, or submit", plus the corrected empty-search description covering both forms. Risk to watch:
prose-only responses (each ends the agent turn and costs a harness nudge) and slower calls (~25 more output
tokens per call).

Memory: the llama-server was killed once (at 17:35) and restarted by the watchdog.
