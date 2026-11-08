# bf-lean (candidate 7, built 2026-11-08)

pub-budget-fit with the four tools the model never calls removed (get_status, get_code_neighbors,
search_similar_code, get_code_subgraph: 0 of 2,683 calls over 99 base-off tasks) and the prompt line that
told it not to use the graph tools. Everything else identical (prompt, temperature 0.2, thinking 4096,
8 min / 28 calls / 80 turns / 240 s).

Mechanism: tool declarations shrink from 4,900 to 2,825 JSON chars (~500 tokens less per request on an
~11.7k-token prompt, ~4%), and the model sees 5 tools instead of 9. Expected effect is small; this is a cheap
LB slot after the queue clears, not a strong bet. COMPILE_OK (tools 5, thinking 4096) on 2026-11-08.
LB day 1 queued for 2026-11-16; the daily routine decides days 2-3 from the other candidates' results
(if think2k/think1k end up best, a lean version of that winner is the better follow-up).
