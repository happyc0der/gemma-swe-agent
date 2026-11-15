# bf-pin (candidate 10, built 2026-11-15)

One change vs the base `pub-budget-fit` (verracodeguacas' budget-fit reference bundle, Apache 2.0, credited in
experiments/variants/pub-budget-fit.CREDIT.md): the system prompt ends with the task statement,

    ## The task statement (repeated here so it stays visible for the whole run)
    {problem_description}
    {hints?}

Everything else is byte-identical. `bf-pin-off` is the thinking-off twin for the T4 faithful eval.

Why:
- The harness fills `problem_description` (and `hints` when a task has them) into the ADK session state
  (swegemma/harness/agent_runner.py), so the two placeholders are substituted on every model call. The scorer
  compacts history above 14,336 context tokens; the first user message with the issue text is among the events that
  get summarised away. Our day-2 prompts (v1-v5) embedded the task for this reason; the budget-fit prompt does not.
- Our own thinking-on offline runs (TPU v6/v7, official Evaluator, same compaction config), solved / tasks by number
  of compactions in the run (a compaction = prompt tokens falling by > 1,500 between consecutive calls):

  | run | 0 | 1 | 2+ |
  |---|---|---|---|
  | pub-budget-fit AB | 6/8 | 6/18 | 1/7 |
  | pub-budget-fit DEV | 5/5 | 7/17 | 1/11 |
  | bf-lean AB | 10/12 | 6/12 | 1/9 |
  | bf-lean DEV | 8/10 | 6/15 | 0/8 |

  About 80% of base tasks compact at least once (first at about the 15th model call) and tasks with two or more
  almost never resolve. This is a correlation (long runs are the hard tasks), not proof that losing the issue text
  is the cause; the candidate tests exactly that.
- Public: Fabrian Ivan Prasetya reports the same cliff over 487 trajectories (48% / 26% / 13% at 0 / 1 / 2
  compactions). Mikkel Chávez Petersen's "LB 0.22 | 3 tweaks" notebook (bundle digest a6c6460094d8) pins the task
  the same way on top of the budget-fit prompt, together with 40 tool calls and a fast-exit rule: one draw of 13.
  We take only the pin (credit for the idea in this form: that notebook; 40 calls is a 12 h runtime risk).

Cost: the issue text is sent twice until the first compaction (a few hundred prompt tokens per call), so
compaction can come slightly earlier.

Plan: thinking-off screen on T4 (bf-pin-off on AB vs base-off 9 and 12 of 33) to rule out a large regression,
thinking-on pair on the TPU lane after v8, LB days 11-21, 11-25, 11-27 (pull them if a screen is <= 7 thinking off
or <= 9 thinking on).
