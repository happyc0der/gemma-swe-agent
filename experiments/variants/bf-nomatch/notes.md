# bf-nomatch = pub-budget-fit + one bullet: a no-match grep is an answer, not an error

Base: `experiments/variants/pub-budget-fit` (verracodeguacas's Budget-Fit Single Agent, Apache 2.0; see
`experiments/variants/pub-budget-fit.CREDIT.md`; files_sha256 c9829b6a). Everything is byte-identical except one
bullet added to "1. Identify Target Files Immediately" in prompts/system.md (~60 tokens):

> A search that finds nothing (`grep` or `git grep` exit code 1) comes back as `status: error` with empty stdout
> and stderr. The command worked: that text is not in those files. Never run the same search again; search a
> shorter or different identifier, widen the path, or read the file the issue names.

## Evidence (our own traces, measured 2026-10-24)
The harness reports any non-zero exit as `{"status": "error", "error_type": "CommandError", "error_message": ""}`,
so a grep with no hits looks like a failed command. Counted over kernel v23 (pub-budget-fit-off, set AB, 33 tasks,
data/faithful_results/bf-off-AB):
- 81 of 396 `run_command` calls (20%) were greps with exit code 1 and empty stdout/stderr; 30 of them exact repeats
  of an earlier command in the same task; 12 tasks had at least one, 11 of those 12 unresolved.
- 5 of the 6 empty-patch tasks contain them. fastapi_14482 ran the same `grep -rn "arbitrary_types_allowed" . | grep
  -v "tests/"` again and again until the 28-call cap, never edited and submitted an empty patch; fastapi_14099 repeated
  a no-match `git grep -n "StreamingResponse" fastapi/routing.py` through the budget warning.
- Kernel v24 (bf-warn-off): 49 no-match greps in 17 tasks, 3 of 8 empty-patch tasks. Our own v6.0 prompt (kernel v21,
  thinking off) hit 51 no-match greps but repeated only 2, so the repeat loop is specific to the budget-fit prompt.
- Our base traces show no context overflows (0 of 33), so the public "keep tool results small" idea (leoprovorov's
  anytime-patch notebook, citing dmitriigluzdov's CC BY 4.0 run dataset) was not chosen as this candidate.
- Counted with `scripts/count_nomatch_greps.py` (status error, exit_code 1, empty stdout/stderr, `grep` in the
  command).

## Runtime
No budget change; the bullet only replaces wasted repeat calls (each ~1-2 model turns), so expected time per task
goes down. Caveat: measured with thinking OFF; the LB base runs thinking 4096 ON, where the loop may be rarer.

## How it is judged
Thinking-off screen first (`bf-nomatch-off` on AB vs pub-budget-fit-off 9/33, kernel after v25), then LB only:
>= 3 LB days interleaved with base days after bf-editfb's; promote only at a mean >= 1.5 tasks above the base's mean
with no runtime failure; drop on any "exceeded the allowed runtime".
