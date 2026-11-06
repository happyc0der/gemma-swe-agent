# bf-think1k (candidate 6, built 2026-11-06)

One change vs the base `pub-budget-fit` (verracodeguacas' budget-fit reference bundle, Apache 2.0, credited in
experiments/variants/pub-budget-fit.CREDIT.md): `thinking_budget` 4096 -> 1024. Everything else is byte-identical.
COMPILE_OK under the 10-12 harness: `thinking_token_budget: 1024`, enable_thinking true, 8 min / 28 calls / 80 turns / 240 s.

Evidence (thinking budget is the one axis where every data point so far is level or better than the base):
- bf-think2k (budget 2048) LB draws 10, 10 (11-01, 11-05) vs base 9.63 over 8 (pooled with 10 public draws 9.83).
- navyadevadiga T8 (thinking_budget 256, 3 tools, Apache 2.0): 12 and 9 of 58 on identical files.
- Mechanism: a full 4096-token thought costs ~2 of the 8 task minutes at the scorer's decode rate, so shorter thoughts
  buy more tool calls per task and lower the 12 h runtime risk; 1024 sits between the 2048 and 256 data points.
- Not screenable offline: the TPU lane ignores thinking_token_budget (experiments/2026-11-05-tpu-v4/notes.md), and the
  T4 lane is faithful only for thinking-off configs. So it goes straight to LB days (3 runs, interleaved).

Verdict rule: promote only if mean over >= 3 LB runs >= base mean + 1.5 with no runtime failure; drop at once on
"exceeded the allowed runtime" (unlikely: shorter thoughts make calls faster).
