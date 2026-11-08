# bf-think1k-lean (candidate 8, built 2026-11-08; NOT queued yet)

= bf-lean (base minus get_status and the 3 code-graph tools, plus the prompt line about them; experiments/variants/bf-lean/notes.md)
with `thinking_budget: 1024` (as bf-think1k). The base
bundle is verracodeguacas' budget-fit reference (Apache 2.0, credited in experiments/variants/pub-budget-fit.CREDIT.md).

Why: Keshav's 11-08 note — if think2k or think1k finishes ahead of the base, a lean version of that config is the better
follow-up to bf-lean. bf-think1k LB day 1 (11-08) = 12/58, the best single draw of any of our configs (base 9.67 over 9).
One draw is within noise (single-draw SD ~1.6), so this variant is only built and compiled, not queued.

Decision rule: queue its LB days only if bf-think1k's mean over its 3 days (11-08, 11-12, 11-14) beats the base mean by
>= 1.0 task; then it replaces bf-lean's day 2/3 slots (or follows bf-lean day 1). Candidate freeze 11-26.

Compile (2026-11-08): COMPILE_OK; thinking {"enable_thinking": true, "thinking_token_budget": 1024}; tools 5; 8 min / 28 calls / 80 turns / 240 s.
