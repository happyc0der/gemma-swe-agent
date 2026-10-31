# bf-t10: the base with Gemma's recommended sampling (temperature 1.0, top_p 0.95, top_k 64)

One change from pub-budget-fit: sampling.yaml temperature 0.2 -> 1.0 and top_k 64 added (Google's recommended
Gemma 4 sampling for all tasks, thinking included). Our thinking-off traces showed verbatim loops at 0.2 that were gone
at 0.7; whether low temperature also hurts the thinking-on base is unknown. Screen on the TPU lane (thinking on, AB,
paired with the base) before any LB day; watch agent time, since longer thoughts push the 12 h runtime.

## 2026-10-31 13:00 UTC: reinstated for LB days (11-03, 11-07, 11-11)
Withdrawn at 08:10 UTC on the thinking-off proxy (bf-t10-off: AB 10/33, DEV 7/33; pooled 17/66 vs base-off ~20/66).
Reinstated five hours later for three reasons, recorded so the reversal is traceable:
1. The proxy has not transferred: bf-nomatch was level offline (31/99 vs 30/99) and scored 8 and 7 on the LB.
   A thinking-off screen therefore neither promotes nor condemns a thinking-on config by itself.
2. New public thinking-on evidence (data, author-reported, not reproduced by us): Fabrian Ivan Prasetya's paper-track
   notebook `fabrianivan/gemma-4-swe-agents-three-paradoxes-ca-hgr` reports two archives (v19, v24) with
   byte-identical agent.yaml, eval_config.yaml and prompt that differ only in configs/sampling.yaml, temperature 0.2
   vs 1.0 / top_p 0.95 / top_k 64, scoring 0.18 and 0.24 on the public LB (11 vs 14 of 58, one draw each; the
   difference is at the edge of one draw's noise). The stated mechanism, repetition loops inside the thought channel
   at low temperature, is the one our thinking-off traces showed (verbatim repeated calls 30% -> 13%), and it should
   matter more with thinking on, where the loops happen inside 4096-token thoughts that the thinking-off proxy never
   generates.
3. Gemma's documented sampling defaults are 1.0 / 0.95 / 64; the base's 0.2 is the public bundle's choice, untested.
Verdict rule unchanged: mean over 3 LB days >= base mean + 1.5 (currently 11.0) with no runtime failure promotes it;
an "exceeded the allowed runtime" error drops it at once (remove the remaining dated queue files).
