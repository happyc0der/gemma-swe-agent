# bf-warn = pub-budget-fit + one paragraph: the budget-warning protocol

Base: `experiments/variants/pub-budget-fit` (verracodeguacas's Budget-Fit Single Agent, Apache 2.0; see
`experiments/variants/pub-budget-fit.CREDIT.md`). Everything is byte-identical except one bullet appended to the
prompt's "Budget" section (prompts/system.md), ~70 tokens:

> Once 10 tool calls remain, every tool result carries a `budget_warning` field. Treat the first one as a hard stop
> for exploration: if you have not edited a source file yet, your very next call must be the edit (best guess,
> `edit_file`); then at most one targeted check, one correction if needed, and `submit_patch`. Never spend a
> post-warning call on reading or searching.

## Evidence
- Harness mechanism (swegemma/tools/base.py): once <= 10 calls remain, `budget_warning` is appended to every tool
  result. Fixed threshold, independent of max_tool_calls, so with the base's 28-call cap it fires from call 19.
- Our thinking-off evals (experiments/2026-10-17-faithful-v57-AB, 2026-10-18-faithful-v58-AB): 9 of the 12 tasks
  that had not edited by call 30 (40-call cap) edited at calls 32-36, i.e. right after the warning; it is the one
  nudge the model reliably obeys. Adding the protocol sentence (v5.7 -> v5.8) went 12/33 -> 14/33 with two
  first-ever solves whose edit came right after the warning (fastapi_15589, fastapi_5624). v6.0's one gain vs v5.9
  (fastapi_15589) again edited at call 33, the call after the warning.
- Runtime: no extra calls, no larger budget; +~70 prompt tokens per step. The 8-min / 28-call family is at the edge
  of the 12 h cap, so the change must not slow calls; this one cannot.

## How it is judged
LB only (thinking on cannot be evaluated offline on T4s): >= 3 LB days interleaved with base days; promote only at
a mean >= 1.5 tasks above the base's mean with no runtime failure; drop on any "exceeded the allowed runtime".
A thinking-off screen of the same sentence on the official starter prompt (pub-budget-fit-off vs bf-warn-off,
kernels v22/v23) runs in parallel as supporting evidence.

## Verdict (2026-10-23, kernel v24 = bf-warn-off on AB)
10/33 vs pub-budget-fit-off 9/33 (noise). At the first `budget_warning` the next call was an edit in only 3 of 23
tasks (base 0 of 23), and the base already called `submit_patch` after the warning in 21 of 23 tasks (bf-warn 22),
so the bullet's intent was already met by the base. Side effect: `edit_file` calls doubled (164 -> 328, 287 without
`old_string`), four tasks hit the 80-turn cap (base two), agent time +14 min. **Withdrawn from the LB queue before
any LB day** (runtime is the binding risk for the 8-min family). Details:
experiments/2026-10-22-faithful-bf-warn-off-AB/notes.md.
