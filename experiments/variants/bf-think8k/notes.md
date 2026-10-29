# bf-think8k: the base with thinking_budget 8192 instead of 4096

One change from pub-budget-fit: thinking_budget 4096 -> 8192 (enforced by vLLM as thinking_token_budget; the
8192-token max_output_tokens cap is unchanged, so a full thought leaves no room for the answer and this tests whether
the 31B ever needs that much). Twin of bf-think2k in the other direction: deeper reasoning per step at the cost of
slower steps. Runtime risk: a full 8192-token thought is ~4 min at the scorer's ~33 tok/s, half the 8-min task budget,
so this can only go to an LB day if the TPU screen shows agent time at or below the base's (the base already fits the
12 h cap with little margin). Screen on the TPU lane (thinking on, AB, paired with the base) together with bf-think2k;
compare solved tasks, agent time and the share of steps that hit the cap.
