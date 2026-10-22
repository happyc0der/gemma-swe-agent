# bf-editfb = pub-budget-fit + one bullet: fall back to a run_command fix script when edit_file errors

Base: `experiments/variants/pub-budget-fit` (verracodeguacas's Budget-Fit Single Agent, Apache 2.0; see
`experiments/variants/pub-budget-fit.CREDIT.md`; files_sha256 c9829b6a, the most-run public file set: 10 public
draws, mean 10.00 of 58, plus our day 26 = 10). Everything is byte-identical except one bullet appended to
"2. Implement the Solution Directly" in prompts/system.md (~75 tokens):

> If `edit_file` returns an error (a missing `old_string`, or no match), do not call `edit_file` again for that
> change. Make the edit with one `run_command` Python script instead: read the file, `assert old in s` with the
> exact lines copied from the file, `s = s.replace(old, new, 1)`, write it back and print `ok`. One script per
> change; never rerun one that failed unchanged.

## Evidence (kernel v23, the base prompt with thinking off, set AB, 2026-10-21)
- 128 of 164 `edit_file` calls failed with the harness error "mandatory input parameters are not present:
  old_string" (the model's call arrives without the `old_string` argument, the backtick-malformed call seen since
  v4.x), and 125 `edit_file` calls were exact repeats of an earlier call in the same task. Only 24 edits returned
  `status: ok`.
- Two tasks (rich_3278, fastapi_5624) burned the whole 80-turn budget on that loop; the malformed calls do not count
  against the 28-call cap, so the call cap never stopped them. 6 of 33 tasks never edited a source file.
- Our own prompts removed `edit_file` altogether in v5.8 and edited through one `run_command` fix script
  (`cat > /tmp/fix.py` heredoc + `python3`); v5.8 had 0 malformed-edit loops and went 12 -> 14/33 together with the
  budget-warning bullet. This candidate keeps `edit_file` for the common case (it worked 24 times) and only adds the
  escape hatch, so it is the smallest change that targets the loop.
- Caveat: v23 is thinking OFF. The LB base runs with thinking 4096 ON, where malformed calls may be rarer; the
  thinking-off twin `bf-editfb-off` (next kernel, v25, after the quota resets 10-24) measures the effect on the
  same 33 tasks against pub-budget-fit-off 9/33.
- Runtime: no extra calls or larger budgets; a fix script is ~+130 output tokens when used, but it replaces a chain
  of failed calls, so the expected per-task time goes down, not up.

## How it is judged
LB only (thinking on cannot be evaluated offline): >= 3 LB days interleaved with base days, after bf-warn's three;
promote only at a mean >= 1.5 tasks above the base's mean with no runtime failure; drop on any "exceeded the
allowed runtime".
