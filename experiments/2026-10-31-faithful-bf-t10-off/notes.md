# bf-t10-off: Gemma's recommended sampling, thinking off (T4 kernels v32, v33)

bf-t10-off = pub-budget-fit-off with temperature 1.0 / top_p 0.95 / top_k 64 instead of temperature 0.2 / top_p 0.95.
Proxy for bf-t10 (the same change on the thinking-on base). Data: data/faithful_results/bf-t10-off-AB (v32).

## v32: subset AB (33 holdout tasks), pushed 10-31 00:03 UTC, ran 00:39-03:32 UTC (~3.45 GPU h)

| run | solved | exact repeated calls | dead-term repeats | 80-turn-cap tasks | no-edit | median first edit | session timeouts | agent time |
|---|---|---|---|---|---|---|---|---|
| base-off AB (v23) | 9/33 | 281/818 (34%) | 38 | 2 | 6 | 20 | 1 | 220 min |
| base-off AB (v29) | 12/33 | 217/807 (27%) | 13 | 1 | 4 | 17 | 2 | 212 min |
| **bf-t10-off AB (v32)** | **10/33** | **91/709 (13%)** | 10 | 0 | 5 | 15 | 0 | **173 min** |

- Score: level with the base (9 and 12; one run moves by ~3).
- Mechanism: a large, clear change. Verbatim repeated calls fall from ~30% to 13%, no task runs into the 80-turn cap,
  first edits come earlier and the run is ~19% faster. Of the base's 5 solved-in-both tasks it lost fastapi_15589 and
  gained fastapi_12942; it solved fastapi_14360 (base 1 of 2) and missed fastapi_5624 and requests_7427 (base 1 of 2).
- Neither llama-server's log nor the traces record the sampling parameters, so whether top_k 64 reached the model is
  unverified (litellm.drop_params can drop it on the OpenAI-compatible route); the repeat drop shows temperature did.

Not a regression (> 7/33), so v33 runs it on subset DEV (33 stable dev tasks; base-off DEV = 9/33, 242 min), pushed
10-31 ~03:40 UTC.
