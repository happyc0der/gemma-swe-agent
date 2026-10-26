# bf-noedit = pub-budget-fit without the `edit_file` tool

Base: `experiments/variants/pub-budget-fit` (verracodeguacas's Budget-Fit Single Agent, Apache 2.0; see
`experiments/variants/pub-budget-fit.CREDIT.md`). One change: `edit_file` is removed from `agent.yaml`, and the one
prompt line that named it (section 2) now says to edit with one `run_command` Python script (read, `assert old in
src`, replace, write back) or `write_file`. Everything else is byte-identical.

## Evidence (thinking-off faithful screens on set AB, 33 tasks)
- Kernel v23 (pub-budget-fit-off, 9/33): 128 of 164 `edit_file` calls failed with "mandatory input parameters are not
  present: old_string"; 125 exact repeats; rich_3278 and fastapi_5624 hit the 80-turn cap on that loop (malformed
  calls do not count against the 28-call cap, so the loop burns turns and wall time instead).
- Kernel v24 (bf-warn-off, 10/33): edit_file calls doubled to 328 (287 missing old_string), 4 tasks at the 80-turn cap.
- Kernel v25 (bf-editfb-off, 7/33): a prompt bullet telling the model to switch to a fix script after an edit_file
  error was followed after 6 of 236 errors. Prompt text does not break the loop, so this candidate removes the tool.
- Our v5.8 (no edit_file, edits via run_command scripts) scored 14/33 on the same set vs 13/33 for v5.0n with it.

## Risks
- Thinking-on LB runs write the script inside the visible answer; a long `write_file` of a whole file costs more
  tokens than an edit. Screen first: kernel v27 = bf-noedit-off on AB vs pub-budget-fit-off 9/33 and bf-nomatch-off
  11/33; also compare agent minutes (base 220) because runtime is the binding LB risk.
- v5.9 showed fix scripts can silently no-op; the `assert old in src` keeps that visible.
