# What the public notebooks do (read 2026-09-29)

Configs pulled with `kaggle kernels pull` into `kaggle/reference/`. Scores are the authors' own claims.

| notebook | claimed LB | sampling | budget per task | structure |
|---|---|---|---|---|
| lucifer19/black-cat-swe-agent-pack-instinct | 0.10 (0.08 single-agent fallback) | temp 0.2, top_p 0.95, top_k 40, 4096 out, thinking off | 5 min, 48 calls, 100 turns, timeout 180 | coder + `second_opinion` advisor sub-agent (1536 out) |
| nihilisticneuralnet/0-10-gemma-4-developer-agent-submission | 0.10 | temp 0.15, 8192 out (2048 for sub-agents), thinking off | 4.5 min, 40 calls, 100 turns, timeout 60 | coder + `code_localizer` + `code_verifier` agent tools |
| zhukovoleksiy/gemma-4-walkthrough-first-submission | 0.10 (v2) | temp 0.2, top_k 40, 4096-8192 out, thinking off | 4 min, 80 turns, timeout 120 | coder + read-only `code_analyzer` |
| mizeroluckygall/pathfinder-gemma-4-agent-eda-baseline | 0.08 | temp 0.2, top_k 40, 8192 out, thinking off | none | coder + analyzer |
| romanrozen/gemma-eda-baseline-for-a-start-lb-top-1 | 0.12 (09-24) | temp 0.2, top_k 40, 8192 out, thinking off | none | coder + analyzer |
| **ours, day 5** | **0.10** | **temp 0.7**, 4096 out, thinking off | 4.5 min, 30 calls, 60 turns, timeout 180 | coder only |

Takeaways:
- Everyone at 0.08-0.12 uses temperature 0.15-0.2 with thinking off. Our 0.7 came from 12B-proxy loops, never
  tested on the 31B.
- Most use an analyzer-style AgentTool. Oleksii's notes: `skip_summarization: true` ends the coder's turn after
  every analyzer call and triggers a harness nudge; he switched to `skip_summarization: false` with a one-line
  request to the analyzer.
- Tool-call caps are 40-48 where set; ours is 30 and our prompt plans ~15 calls.
- Nobody public is above 0.12; the leaderboard top (0.13-0.15) is private.

Plan, one change per day on top of day 5 (0.10): day 7 temperature 0.2 + top_k 40; then a higher call cap with
a relaxed call plan; then an analyzer sub-agent with `skip_summarization: false`.

## Results so far (2026-09-30)
- Day 7, temperature 0.2 + top_k 40: **0.10**, the same as day 5 at temperature 0.7. Neither the budget above 4.5 min
  nor the temperature moves the score beyond the ~1-2 task noise band.
- Day 8 (2026-10-01): agents were ending early by choice (runs finish in ~6.5-7 h), so prompt v4.4 plans ~25 calls
  (was ~15), caps at 40 calls / 80 turns (was 30 / 60), and calls submit_patch as soon as the reproduction passes and
  again after later edits. In the official runner a context-overflow error skips the working-tree fallback and
  loses unsubmitted work, while submit_patch is free and does not end the session.

## 2026-10-11 (daily routine)
- `dmitriigluzdov/gemma-4-measure-before-you-tune` (63 votes, run 10-11): reports that the public **Budget-Fit single
  agent** bundle (`verracodeguacas/gemma-4-agent-budget-fit-single-agent`) reproduces **0.18** on the public LB (their
  submission 56932359), vs our 0.06-0.10. Config: one coder, **8 min / 28 tool calls / 80 turns, thinking budget 4,096
  ON**, command timeout 240 s. Same author saw one byte-identical archive score 0.10 and 0.06 on different days (LB
  noise ~0.06), and estimates 120 hidden tasks run sequentially in 12 h => ~282-350 s/task average, so long budgets only
  fit if most tasks end early. Our own "thinking on loses" result (6/16 vs 9/16) was at a 3.5-min (x3) budget where
  thinking caused session timeouts; an 8-min budget is untested here. Not adopted: needs Keshav's decision and an
  offline AB eval under the ship rule.

## 2026-10-12 (daily routine)
- `hitarthjain0/gemma-4-apex-silver-agent-lb-0-24` credits `honghanhhh/gemma-4-baseline-lb-0-24` with a **0.24** public
  score for a "contract-first" single agent on the Budget-Fit limits (8 min / 28 calls / 80 turns / 240 s, thinking
  budget 4096 ON, max_output_tokens 8192, temperature 0.2). Prompt ideas: copy the issue's exact names/strings/status
  codes before searching; one `git grep` then a <=120-line read; source edit by call 12; at most one focused check and
  one repair; scratch files in /tmp and test paths checked out before submit_patch; graph tools not registered. The
  notebook's own 0.24 is claimed, not shown. This is the same budget/thinking family as our pending day-17 LB test
  (`v50n-think8`), so that score decides whether this direction is worth an offline AB eval.

## 2026-10-15: contract-first bundle staged as a one-day LB test (Keshav's choice)
- Source: `honghanhhh/gemma-4-baseline-lb-0-24` ("v3 (0.22 config + targeted prompt edits)", based on the public
  `gemma-4-budget-aware-coding-agent-v2`, reported 0.22; the 0.24 title is claimed, not shown). Public Kaggle notebook,
  no explicit license (Kaggle's default for public code is Apache 2.0); used as-is for a test, credited here.
- Bundle copied byte-for-byte to `experiments/variants/pub-contract-first` (extracted from the notebook's embedded
  `FILES`): temperature 0.2, top_p 0.95, max_output_tokens 8192, thinking_budget 4096 + include_thoughts true, tools
  incl. read_file and the three graph tools (prompt forbids the graph tools), 8 min / 28 calls / 80 turns / 240 s.
- Prompt ideas vs ours: a hard call plan (edit by call 12, nothing new after call 20), "an unedited tree always
  scores zero", spec extraction before searching, batched git grep, at most 2 verify calls, every parallel
  implementation (sync/async, overloads, `__all__`), FastAPI `docs_src/` executable docs, never conclude no change.
- Compiles under the current harness (COMPILE_OK, enable_thinking true, thinking_token_budget 4096, 9 tools).
- Judge on the LB: if it reproduces >= 0.17 (10/58) the gap to our ~0.10 is prompt + config and we build on it
  (offline AB eval of our prompt in this style); if <= 0.12, the claim does not hold for us and v5.0n stays.

## 2026-10-17: dmitriigluzdov 'Gemma 4: Public Agent Ideas and Evidence' (updated)
- Catalogue of 187 public notebooks; a paired local screen on 31 tasks finds no established gain among budget-fit
  variants (9 vs 9 vs 8 vs 8 solved, sign tests p = 1.0). The same coder-analyzer archive scored 0.06-0.12 across
  runs, which matches our view that 1-2 task LB differences are noise.
- Its arithmetic projection puts 8-minute budget-fit configs at 11.6-13.0 h for ~120 tasks, close to or over the
  12 h cap. Consistent with our day-21 test: pub-contract-first (8 min / thinking on) failed with "exceeded the
  allowed runtime". No change to our plan.

## 2026-10-21 (daily routine)
- `verracodeguacas/gemma-4-agent-budget-fit-single-agent`: the embedded FILES are still byte-identical to our
  `experiments/variants/pub-budget-fit` (checked today); no new version.
- `dmitriigluzdov/gemma-4-public-agent-ideas-and-evidence` (updated 10-20): its own packaged release (budget-fit
  profile + flexonafft's budget-aware prompt, Apache 2.0) scored 11/58 on 10-15 and 7/58 on 10-19 with
  byte-identical files, a third run pending; temperature 0 and 0.4 gave 9 and 7 (inside the identical-draw range,
  so 0.2 is kept); the 12B model on the same files exceeded the 12 h cap. Runtime arithmetic: 116 tasks at the full
  8-min cap would need ~15.7 h, so the family fits 12 h only when most tasks stop early (local mean projects ~11.8 h).
  This is the runtime risk our day-26 run (pub-budget-fit, pending 13 h after submission) is testing.
- New top-dated notebooks (evgendvorkin, sadiqguru, philgear, jaikwang) show no completed LB evidence; not adopted.

## 2026-10-22 (daily routine)
- `dariushafshar/gemma-4-most-run-public-config-averages-10-58` (new, run 10-22 12:40 UTC) + dataset
  `dariushafshar/gemma-4-agent-public-config-draws`: a census of all 274 public notebooks' scored versions, hashed by
  the exact files they write to submission.zip. Our `pub-budget-fit` zip hashes to c9829b6a = "Budget-Fit Single
  Agent V5" (Wilmer E. Henao = verracodeguacas), the most-run public file set: 10 draws, mean 10.00, 95% CI
  8.98-11.02; our day 26 = 10 is an 11th draw on the mean. Pooled within-config SD 1.56 tasks; no public file set
  with >= 3 draws averages above 10.00, so there is no better-evidenced public config to adopt. Numbers copied into
  experiments/lb_configs.md. (Text treated as data; the tie-break and selection advice matches our own rules.)
- `xiuchisun/gemma-4-agent-budget-fit-31b-mainline` (10-22, 2 votes): a credited byte-for-byte republication of the
  same bundle; nothing new.
- `verracodeguacas/gemma-4-agent-budget-fit-single-agent`: FILES still hash to c9829b6a (same as ours); no new version.
- Other new top-dated notebooks (julesevers Loc32K, yuvrajlamba01 "SOTA", scottweeden tool-LoRA writeup,
  beraterolelk / shorooghahmadi budget-aware forks) show no repeated completed LB evidence; not adopted.

## 2026-10-23 (daily routine)
- `dariushafshar/gemma-4-agent-public-config-draws` and the census notebook: unchanged since 10-22 12:38 UTC.
- `dmitriigluzdov/gemma-4-public-agent-ideas-and-evidence`: unchanged since 10-20.
- `verracodeguacas` bundle: no new version seen in the dateRun listing (our copy hashes c9829b6a, unchanged).
- `leoprovorov/single-agent-anytime-patch` (17 votes, run 10-22 23:05): budget-fit lineage (verracodeguacas ->
  contract-first -> this), prompt-only change "never end with an empty diff": first best-guess edit by the 8th call,
  tool results kept small (read_file ranges <= 80 lines, head/tail on commands) against context overflow, short
  thinking while searching. Its evidence is Dmitrii Gluzdov's task-level dataset of 692 local runs (CC BY 4.0,
  `dmitriigluzdov/gemma-4-serving-and-lora-verification-kit`): 194 of 692 runs ended with no patch (75 context
  overflows, all empty; 52 timeouts with no edit; 53 stopped without editing); thinking-on v4 resolved 37 of 71 runs
  that used <= 14 calls vs 2 of 43 that went 15-20 calls. **No LB run yet** ("submit once the previous finishes"),
  so not adopted; worth re-checking for completed draws. The dataset itself is a candidate source for the paper's
  failure taxonomy (public numbers, properly credited).
- `ryanholbrook/gemma-4-developer-agent-small-model-leaderboard` (host, 28 votes): the Small Model Prize track
  leaderboard; we run the 31B model, so not eligible; nothing to adopt.
- `robinamirbahar` posted ~10 "loop-breaker" notebooks today (0 votes, no LB evidence shown in the listing); not read.
- `honghanhhh/gemma-4-baseline-lb-0-24` reran 10-23 08:11 (60 votes); that family exceeded 12 h for us on 10-16,
  so it stays dropped regardless of new versions.

## 2026-10-24 (daily routine)
- `dariushafshar/gemma-4-agent-public-config-draws`: unchanged since 10-22 12:37 UTC.
- `lynnsakurai/gemma-4-budget-fit-agent-w-bounded-rescue` (16 votes, run 10-24 08:36): budget-fit limits and sampling
  (8 min / 28 calls / 80 turns, temp 0.2, thinking 4096) with a different prompt ("budget-aware, tool-aligned repair
  agent"); no LB score or repeated draws stated in the notebook. Not adopted.
- `leoprovorov/single-agent-anytime-patch`: still states "Not measured on the leaderboard"; no completed draws. Its
  context-overflow fix is not supported by our own traces (0 overflows in 33 base tasks), so not adopted.
- Others in the dateRun listing (getting-started forks, haosky1 contract-first fork, robinamirbahar loop-breaker
  series, LoRA training, A/B notebooks) show no repeated completed LB evidence; not read further.

## 2026-10-26 (daily run)
- Wheelhouse unchanged (10-12 19:51); census dataset dariushafshar/gemma-4-agent-public-config-draws unchanged (10-22).
- New in the dateRun listing: robinamirbahar loop-breaker ADK agent, karandeepsinghsodhi SFD (state-filtered
  deliberation) and its paired-eval shards, cosmorin V32/Idris replicas, jocelyndumlao vLLM benchmark, getting-started
  forks. None shows repeated completed LB draws, so none adopted; not read further.

## 2026-10-27 (daily run)
- Wheelhouse unchanged (10-12 19:51); census dataset unchanged (10-22 12:38).
- New in the dateRun listing: prvsiyan explainer notebooks, alikalwar lean submission.zip builder and "shortlist-first
  opening" measurement, jasonxusk fusion repair agent, karandeepsinghsodhi SFD shards, getting-started forks. None
  shows repeated completed LB draws; none adopted. ryanholbrook Small Model leaderboard: 31B entries are not eligible.

## 2026-10-29 (daily run, 13:00 UTC)
- Wheelhouse unchanged (10-12 19:51); census dataset dariushafshar/gemma-4-agent-public-config-draws unchanged (10-22 12:37).
- `harshitsama/gemma-4-agent-is-0-24-vs-0-22-real-noise-check` (run 10-28): simulation only, no new LB draws; its
  conclusion (one run of the same agent moves 1.5-3 tasks; 0.24 = 14 tasks over 6 teams; judge by repeats) matches our
  own noise analysis (lb_configs.md, paper). Nothing to adopt.
- `dennis6886/gemma-4-agent-0-18-exact-budget-aware-package` (run 10-27): one more completed draw of flexonafft
  Budget-Aware v2 V10 files = 0.18 (11/58); that family's census draws were 13, 7, 7, 8, 9, 10, 10, 7, 9 (mean 9.25
  over 8 before this). Still not above the base's public mean 10.00; not adopted.
- `prvsiyan/gemma-4-agent-bundles-side-by-side-what-changes` (run 10-29): reads two public ZIPs (flexonafft V10,
  cosmorin Idris v24 replica), no measurement; mentions one candidate (max_output_tokens 8192 -> 12288, score
  "pending"). No evidence; not adopted. Idris v24 (claimed 0.24) is author-reported only.
- Others in the dateRun listing (getting-started forks, E2B LoRA, small-model entries, trace analytics, SFD shards):
  no repeated completed LB evidence; not read further.

## 2026-10-30 (daily run, 13:00 UTC)
- Wheelhouse unchanged (10-12 19:51); census dataset dariushafshar/gemma-4-agent-public-config-draws unchanged (10-22 12:38).
- `cosmorin/gemma-4-timeout300-tools6-lb-0-18-reproduction` (run 10-29): honghanhhh v6 prompt + two settings taken
  from davis0178's package (team DVS, board 0.22 over 24 submissions): `timeout_seconds` 240 -> 300 and the three graph
  tools dropped from agent.yaml (6 tools). One completed draw = 0.18 (11/58); the author's previous draws of the same
  prompt were <= 0.13. Checked against our own base traces (pub-budget-fit-off, 99 tasks over AB, AB rerun and DEV):
  **0 graph-tool calls and 0 command timeouts**, although the "Code Intelligence Tools" section was present in all 33
  logs per run. Neither setting has a mechanism in our traces (the only effect of dropping the tools would be three
  fewer function declarations per step, which vLLM prefix caching already absorbs), so not adopted; one draw at 11 is
  inside the base's noise band anyway.
- `victorzhong0110/same-bytes-two-scores` (run 10-30): flexonafft upstream-v8 pack, one archive (sha256 205a677f...)
  submitted twice: 0.13 and 0.17 (8 vs 10 tasks). Board snapshot 10-28 02:34 UTC: 0.24 x5, 0.22 x48, 0.20 x214,
  0.18 x562 (ranks 268-829; bronze = top 397, so 0.20 = 12/58 clears it), 0.17 x678. Confirms our noise analysis;
  useful for the paper's LB-noise section (credit when cited). Nothing to adopt.
- `victorzhong0110/config-regression-on-a-public-eval-set`, `one-submission-a-day-sampling`: method notebooks on a
  synthetic benchmark; no LB draws. Others new in the dateRun listing (shipship forks of lb024/baseline, boristown E2B
  LoRA, denpugovkin before/after check, hl54378 three-tool baseline, dheerajkr1a1a Idris replica): no repeated completed
  LB evidence; not read further.

## 2026-10-31 (daily run, 13:00 UTC)
- Wheelhouse unchanged (both pages of `kaggle datasets files`, newest 10-12 19:51 UTC).
- `navyadevadiga/gemma4-swe-agent-t8-static` (run 10-31, Apache 2.0): a static bundle with 3 tools (run_command,
  read_file, submit_patch), temp 0.3 / top_p 0.95 / top_k 64, **thinking_budget 256** + include_thoughts, 8 min / 25
  calls / 40 turns / 240 s, edits via Python scripts in run_command. Author-reported **0.20 (10-23) and 0.15 (10-28)
  with identical files** (12 and 9 of 58; mean 10.5 over 2, within noise of the base's 10.0 over 10). Two completed
  draws is not enough to adopt the bundle, but it is independent evidence that a very short thinking budget does not
  hurt, which supports bf-think2k (queued for 11-01, 11-05, 11-09). Credited in lb_configs.md.
- `fabrianivan/gemma-4-swe-agents-three-paradoxes-ca-hgr` (paper-track notebook, run 10-31): claims (data, not
  reproduced by us) (a) v19 vs v24 archives with byte-identical agent.yaml / eval_config / prompt, differing only in
  sampling (temp 0.2 vs 1.0 / top_p 0.95 / top_k 64): LB 0.18 vs 0.24, one draw each; mechanism given: repetition
  loops inside the thought channel at low temperature; (b) a compaction cliff (resolution 48% -> 26% -> 13% at 0/1/2
  history compactions over 487 trajectories; threshold 14,336 tokens) and a first-edit window (steps 5-12: 43-48%
  resolved vs 24% later); (c) LoRA r=16 SFT on SWE-smith/SWE-rebench trajectories lowered loss but cut paired 46-task
  resolution from 39% to 28% and 20%. (a) is the reason bf-t10 is reinstated for LB days (its notes.md); (b) goes
  into the paper's external-check paragraph with credit; (c) agrees with our decision to leave LoRA alone.
- `alepacheco/graphread-reproduce` (run 10-31): CPU reproduction of a paper on whether Gemma 4 can read the harness's
  graph tools; counts graph-tool calls in three public trace sets. Consistent with our 0 graph-tool calls in 2683
  calls; nothing to adopt.
- `victorzhong0110/pricing-your-change-offline-to-leaderboard`, `kaggle-medal-cutoff-and-expert-tier-tracker` (run
  10-31): method notebooks (offline-to-LB transfer ratio on a synthetic benchmark; medal cut-off arithmetic: bronze =
  top 100 for 250-999 teams, top 10% above 1000; ties go to the earlier submission). No LB draws; nothing to adopt.
- Others new in the listing (shipship v3, emmanuelmirekumensah honghanhhh config, GemmaLoc, E4B taxonomy, graph
  benchmark): no repeated completed LB evidence; not read further.

## 2026-11-01 (daily run, 14:00 UTC)
- Wheelhouse unchanged (newest file 10-12 19:51 UTC).
- `prvsiyan/gemma-4-agent-bundles-side-by-side-what-changes` and `what-s-in-the-bundle` (run 11-01): static
  bundle-anatomy notebooks on the flexonafft lineage. Their own lane: best completed 0.18, latest 0.12 (an
  "output-cap" candidate, one draw); seven one-setting candidates (top_p 0.96, timeout 150, temperature 0.18, call cap
  44, turn cap 104, 12B with 1.5x thinking) all unscored. Board-top snapshot 0.29 on 10-31 23:36 UTC (data). Nothing
  to adopt.
- `victorzhong0110/config-regression-on-a-public-eval-set` (run 10-31): method notebook (paired comparison on a
  scoreable set, "same code, different score"); no LB draws; agrees with our noise analysis. Nothing to adopt.
- Others new in the listing (boristown E2B LoRA baseline, trnvnhin 31B LoRA SFT v1, krishnakumarbhat, zfayfay,
  abhaychaudhary01, mohammadalrashed, alepacheco testsel): no repeated completed LB evidence; not read further.
- Checked whether the ADK history compaction that fabrianivan links to failures (48% -> 26% -> 13% resolved at 0/1/2
  compactions) is a bundle setting: `grep -ri compaction` over adk_submission and adk_eval_core finds it only in the
  trace/viewer code, so a bundle cannot change the compaction threshold; no candidate from it.

## 2026-11-02 (daily run, 14:00 UTC)
- Wheelhouse unchanged (newest file 10-12 19:51 UTC).
- `leoprovorov/single-agent-anytime-patch` (run 11-01, 17 votes): budget-fit lineage (via a contract-first fork), prompt-only
  edits: first best-guess edit by the 8th call (was 12th), "keep every tool result small" (read_file <= 80 lines, head/tail),
  "think in one or two sentences while reading". Not measured on the LB (the notebook says so). Its evidence is Gluzdov's
  692 local runs: 28% no patch; thinking-on v4 resolved 52% when done within 14 calls, 5% at 15-20 calls. We checked
  the same split on our 99 base-off tasks (experiments/2026-11-02-first-edit-analysis): first edit by call 12 -> 24/37
  solved, later -> 6/45, never -> 0/17; the base prompt's own "edit by call 12" rule is not obeyed (median first edit
  17-20), so a prompt-number change is not adopted. Credit if any later candidate uses the idea.
- `leoprovorov/score-to-gemma-4` (48 votes): writes the budget-fit file set unchanged (sha c9829b6a, = our base),
  expects ~0.17 (0.13-0.20) from the census; also notes a one-line contract check on a neighbouring base scored 0.15
  once and that a 0.22 was the best of eight draws averaging 0.156. Agrees with our noise analysis; nothing to adopt.
- `emmanuelmirekumensah/gemma-flexonafft-budget-v2`: SuperAgent adaptation 0.18 once; this candidate unscored. Nothing to adopt.
- `designmasterdms/where-the-fix-lives`, `jagadish2740/anchor-propagate-pack-reproducing-the-paper` (E4B localisation
  and graph-ranking studies), `ryanholbrook/...small-model-leaderboard` (official, small-model board): no bundle
  config evidence; not adopted.
- Others new in the listing (anhtunnguyen, alfira17, ziadsamer, visuartestudio, zikangzhou, harigov63, tersoouganden,
  smitbailwal, rishikeshbharatkoli, hariom28, krishnakumarbhat, aryasumant): no repeated completed LB evidence.

## 2026-11-05 (daily run; notebook text read as data)

- `pablodiegoo/gemma-4-paper-l4-decode-law-12-call-cliff`: paper-track notebook citing the 692-run census. Its "leftover
  reproducer scripts contaminate `git diff`" trap (also honghanhhh's v6 edit 3 and alexust's scratch-file line) checked on
  our 66 base-off tasks (bf-off-AB + bf-pair-DEV, 18 resolved): 21 of 47 non-empty patches carry a new repro script, and those
  solve **more** often (11/21 vs 7/26 clean), so stray scripts are not sinking tasks here. Not a candidate.
- `alexust/one-bundle-three-outcomes-0-24-0-17-no-score`: the honghanhhh bundle byte for byte drew 0.24, 0.17 and "exceeded
  the allowed runtime"; its 7-minute variant finished at 0.15. Their 101 timed local runs put the 8-minute cap at about 12 h
  for 120 tasks. Same caps as our base, which has never hit the cap in 9 LB runs; keep watching for that error.
- `dennis6886/gemma-budget-evidence-fusion-1105` (one more decision rule on the flexonafft lineage; says itself that it is
  unverified), `tomaszszyrowski/gemma4-zero-bloat-repo-agent` (local workflow plus a bundle; no repeated LB draws): not adopted.
- Board 11-05 (4788 teams): top 0.29 once, then nine at 0.24 with a median of 21 submissions, five of them dated 11-04; we are
  rank 888 at 0.18 with 38 submissions. Best-of-many-draws explains most of this; no public config with repeated draws
  above our base has appeared. Nothing to adopt.

## 2026-11-06 (daily run; notebook text read as data)

- `robinamirbahar/optimizing-w4a16-thinking-budgets-under-time-caps` (paper track): a "240-run" thinking-budget sweep loaded
  from CSV files the notebook ships; no bundle, no LB draws, nothing reproducible against the scorer. Not adopted. Its
  topic matches our bf-think2k / bf-think1k line, whose evidence stays our own LB draws plus navyadevadiga T8.
- `robinamirbahar/gemma-4-loop-breaker-adk-agent` (17 votes) and its CCR/Trap-25 companions: loop-breaker agent; no
  repeated completed LB draws shown. Not adopted.
- Others new (engziadsamer, michaelflorida, pablodiegoo paper starter, hinam74, vianneykakooza, tomaszszyrowski AST
  ensemble, nooktablet E4B SFT/eval set, pikler, primalhost, kawh1111, quangleealex, krisshah123): no repeated
  completed LB evidence for a 31B bundle config. Nothing adopted.

## 2026-11-07 (daily run; notebook text read as data)

- `haroldcooper2/gemma-4-exp5-output8192-budgetfit`: budget-fit-style bundle with a longer graph-first, context-guard
  prompt and a larger output budget; no LB draws shown. Not adopted.
- Others new (janholoubek paper-repro a/b, madhanmohankumar lexical anchors, giuseppecastelluccio GemmaLoc,
  niraberman commit anatomy / find-early-commit-late, grandmastashake edit gate, liuchun1232325 localization,
  alepacheco graphread, munirghanem, namng74, starksource, spiritofvishwakarma, itsailos, apihpih E4B, ryanholbrook
  small-model board): paper-track write-ups or unscored bundles; no repeated completed LB evidence for a 31B bundle
  config. Nothing adopted.

- 2026-11-10: ccuuuuy "LB 0.22 | 4 config files, no training" writes the budget-fit bundle with digest c9829b6ac709, i.e. byte-identical to our base (pub-budget-fit). Its title claims one 0.22 draw (13/58), inside the base's known spread (8-11 in our 9 draws, one public 13 in the family). Nothing to adopt. Other new titles (code-graph toolkit audit, Evidence-per-Token reproduction, Repair Lab, RepoMem) carry no repeated LB draws.

- 2026-11-11: titles skimmed (30 most recently run): mostly paper-track notebooks (noise/MDE, graph benchmarks, harness calibration, loop-breaker telemetry) plus flexonafft "Budget Experimental" and aminebrahimzadeh68 "Before Best-of-N code release"; none shows repeated completed LB draws. Nothing adopted. Board: top 0.29, then a 0.24 block.

- 2026-11-12: titles skimmed (30 most recently run): paper-track notebooks (localization audits, graph-retrieval studies, commit-pinned environments, paired local comparisons), flexonafft "Budget Experimental" again, E4B/E2B small-model bundles; none shows repeated completed LB draws for a 31B bundle config. Nothing adopted.

- 2026-11-13: titles skimmed (25 most recently run): starter forks, a "zaic-lm/dm" series of training/confirmation notebooks from several accounts (no bundle config or LB draws shown), flexonafft "Budget Experimental", denpugovkin "Repair Lab", ccuuuuy "LB 0.22" (byte-identical to our base, noted 11-10). None shows repeated completed LB draws for a 31B bundle config. Nothing adopted. Board: top 0.29, then a 0.24 block.

- 2026-11-14: titles skimmed (30 most recently run): starter forks, the "zaic-lm/dm" series, denpugovkin "Repair Lab", a paper starter, and flexonafft "Budget-Aware Coding Agent: Lean Context" (new title, 0 votes, no LB draws seen; same direction as our bf-lean, which is already on its LB days). None shows repeated completed LB draws for a 31B bundle config. Nothing adopted. Board: top 0.29, then a 0.24 block.
