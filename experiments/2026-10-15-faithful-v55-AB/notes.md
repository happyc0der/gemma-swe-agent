# Faithful eval: v5.5 on set AB (all 33 holdout tasks), kernel v16

Kernel v16, 10-15 13:04 UTC to 17:34 UTC (4.49 GPU h, ALL_DONE). Harness swegemma 0.2.11 / adk_submission 0.2.13
(wheelhouse of 2026-10-12), llama.cpp 71ad0590f, canary passed (fastapi_14303 solved, median 37 tokens/step), 4 GB
`ulimit -v` cap on sandbox commands, no llama-server OOM kill this run. Raw results: `data/faithful_results/v55-AB/`.

v5.5 = v5.0n + the harness `read_file` tool (start/end lines, <= 100 lines per read) in place of `sed -n` reads.

## Result vs v5.0n (new harness: v13 set A + v12 set B)

| | v5.0n | v5.5 (v16) |
|---|---|---|
| solved, 33 tasks | 13/33 | **9/33** |
| changed tasks | fastapi_12942, fastapi_13537, fastapi_14360, fastapi_14485, rich_3777 solved | fastapi_5624 solved |
| no-edit tasks | 4 | 11 |
| exact repeat calls | 184 of 1061 (17%) | **420 of 1169 (36%)** |
| paging >= 4 reads | 11 tasks | 0 tasks |
| "mandatory input parameters are not present" | 81 hits in 6 tasks | **225 hits in 5 tasks** |
| tool calls with leaked `<tool_call\|>` tokens / backtick-closed strings | 0 | 258 in 8 tasks |
| session timeouts | 4 | 5 |
| median output tokens/step | 34-36 | 40 |

**Decision: loses 4 tasks net; v5.0n stays the submission.**

## What happened
read_file removed paging (0 tasks with >= 4 consecutive reads) but brought a new failure: the model closes the
`filepath` string with a backtick and runs the integer arguments and the next tool call into it
(`"fastapi/responses.py\`,start_line:20,end_line:60}<tool_call|>..."`). Once one malformed call is in context, the
following edit_file calls copy the same broken delimiter: new_string ends in `` `,old_string: `` and the harness
reports old_string missing, 20-60 times in a row (fastapi_14964: 30 consecutive identical failing edit_file calls).
7 of the 8 affected tasks started with a malformed read_file right after a run_command.

## The broader pattern (all runs since 10-10)
Malformed calls by tool across v5.0n A/B, v5.3, v5.4, v5.5 traces: edit_file ~700, read_file ~250, write_file 2,
**run_command 1 of ~5,600**. Every failure is a string argument that is followed by another argument (edit_file's
alphabetical order is filepath, new_string, old_string, so the broken close of new_string swallows old_string).
Single-argument run_command calls essentially never break. v5.0n itself loses rich_3061, rich_3278 and
fastapi_14482 to these edit_file loops, and its prompt rule "never resend a malformed call" is ignored.

## Next (v5.6)
v5.6 = v5.0n with edit_file removed from the tool list: every change to an existing file goes through one
run_command heredoc `/tmp/fix.py` (`OLD = r'''...'''`, `NEW = r'''...'''`, assert count == 1, replace), the pattern
v5.0n already uses as its fallback. write_file stays for new files. Kernel v17 runs it on AB.
