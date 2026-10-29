# bf-think2k: the base with thinking_budget 2048 instead of 4096

One change from pub-budget-fit: thinking_budget 4096 -> 2048 (enforced by vLLM as thinking_token_budget). A full
4096-token thought costs ~2 min at the scorer's estimated ~33 tok/s, a quarter of the 8-min task budget, so a smaller
cap trades depth per step for more steps and a shorter run. Screen on the TPU lane (thinking on, AB, paired with the
base) before any LB day; compare solved tasks, agent time and the share of steps that hit the cap.
