# bf-t10: the base with Gemma's recommended sampling (temperature 1.0, top_p 0.95, top_k 64)

One change from pub-budget-fit: sampling.yaml temperature 0.2 -> 1.0 and top_k 64 added (Google's recommended
Gemma 4 sampling for all tasks, thinking included). Our thinking-off traces showed verbatim loops at 0.2 that were gone
at 0.7; whether low temperature also hurts the thinking-on base is unknown. Screen on the TPU lane (thinking on, AB,
paired with the base) before any LB day; watch agent time, since longer thoughts push the 12 h runtime.
