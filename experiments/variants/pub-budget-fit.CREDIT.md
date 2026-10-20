# pub-budget-fit: credit and provenance

`experiments/variants/pub-budget-fit/` is the public **Budget-Fit Single Agent** bundle by **verracodeguacas**
(https://www.kaggle.com/code/verracodeguacas/gemma-4-agent-budget-fit-single-agent, Apache 2.0), extracted
byte-for-byte from the notebook's embedded `FILES` on 2026-10-20. Its prompt is the competition's official
`sample_submission` prompt with budget edits; configuration: temperature 0.2, top_p 0.95, max_output_tokens 8192,
thinking_budget 4096 + include_thoughts true, 8 min / 28 calls / 80 turns / 240 s command timeout.

Evidence for adopting it (dmitriigluzdov, "Gemma 4: Public Agent Ideas and Evidence", citing Darius Hafshar's
leaderboard analysis): seven public runs of the reference files solved 8-11 of 58 public tasks (mean ~10), versus a
mean of ~6 for our own configs over 12+ runs. Adopted as the daily submission on 2026-10-20 at Keshav's request; our
own work (prompt v5.x, the faithful offline eval, the failure taxonomy) continues on top of it.
