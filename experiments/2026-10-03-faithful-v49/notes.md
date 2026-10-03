# Faithful eval: prompt v4.9 (one-line note before every call) vs v4.6-v4.8 (same 16 holdout tasks)

Kernel `dankaxon/gemma4-faithful-eval` v5, T4x2, 18:31-21:40 UTC (151 min of agent runs, 3.1 GPU h with setup).
Metrics: `python3 scripts/faithful_metrics.py <results dirs>`.

| metric | v4.6 | v4.7 | v4.8 | v4.9 |
|---|---|---|---|---|
| solved | 8 | 8 | 8 | **7** (lost fastapi_14360, solved in every earlier run) |
| tasks with no edit | 3 | 1 | 1 | 4 |
| session timeouts | 2 | 2 | 2 | 4 |
| exact repeat calls | 33 | 61 | 76 | 94 |
| steps with a text note before the call | 0 | 0 | 0 | **0** |
| prose-only replies before the last step | 0 | 0 | 0 | **7** |
| agent time | 110 min | 116 min | 123 min | 151 min |

Verdict: worse; day 10 stays v4.7 at 4.5 min, and the note is dropped.

What happened:
- The model never wrote a plain-text note. Asked to reason before each call with thinking switched off, it
  emitted empty thinking-channel markers instead (`<|channel>thought <channel|>` repeated) in 7 replies with no
  tool call; each ends the agent turn and costs a harness nudge. Lesson: with `include_thoughts: false`, do not
  ask Gemma 4 for visible reasoning before calls; it reaches for the suppressed thought channel.
- fastapi_14360: the model closed `new_string` with a stray backtick, so `old_string` was swallowed into it, and
  resent the identical malformed `edit_file` call ~30 times. Calls the tool rejects for missing parameters do not
  count toward `max_tool_calls` (15 counted, 56 LLM calls), so the loop ran until the 10.5-min session timeout.
  The same "mandatory input parameters are not present" loop appears in v4.6 (1) and v4.7 (11, mostly rich_3052).

Next (v5.0n = v4.8 + corrected empty-search rule + grep instead of paging + behaviour before docstrings + fix sibling
functions + "a missing-parameter error means the call was malformed: never resend it, use /tmp/fix.py").
