# Per-config leaderboard tally

Public LB = 58 tasks; score = solved/58 truncated to two decimals (0.10 = 6, 0.12 = 7, 0.17 = 10). Identical files
differ by several tasks between runs, so configs are judged by their mean over several LB runs, never by one day.
Source of every row: `experiments/kaggle_submissions.md`. Created 2026-10-21 from that log; updated by the daily routine.

| config (variant dir) | family | LB days (UTC submission date) | solved tasks per run | n | mean | failures |
|---|---|---|---|---|---|---|
| **pub-budget-fit** (daily base since 10-21; files_sha256 c9829b6a = the most-run public file set) | official starter prompt + budget edits, temp 0.2, thinking 4096 on, 8 min / 28 calls / 80 turns / 240 s | 10-21, 10-22, 10-23, 10-24, 10-25, 10-26, 10-29 | 10, fail, 9, 8, 9, 11, 10 | 6 | 9.5 (public draws of the same files: 11, 9, 11, 10, 8, 9, 11, 11, 10, 10 -> 10.00 over 10; pooled 16 draws 9.81) | 10-22: "unhandled error" (not the 12 h cap), identical files; the 10-23 retry completed (9), so the error was run-specific; staged again for 10-25 and 10-26 with line 3 = v58-t45 |
| bf-warn (candidate 1, withdrawn 10-23) | pub-budget-fit + one budget-warning bullet | none (withdrawn before any LB day: thinking-off screen 10/33 vs 9/33, bullet followed 3/23, edit_file loops doubled; experiments/2026-10-22-faithful-bf-warn-off-AB) | - | 0 | - | - |
| bf-editfb (candidate 2, withdrawn 10-25) | pub-budget-fit + one edit_file-error fallback bullet (fix script) | none (withdrawn 10-25 before its LB day: thinking-off screen kernel v25 = 7/33 vs base twin 9/33, no-edit tasks 10 vs 6, fallback followed after 6 of 236 edit_file errors in 2 tasks; experiments/2026-10-24-faithful-bf-editfb-off-AB) | - | 0 | - | - |
| bf-nomatch (candidate 3, dropped 10-31 after 2 LB days) | pub-budget-fit + one bullet: a no-match grep (exit 1, reported as status error) means the text is absent; never repeat it | 10-27 (13:03 UTC) = 8, 10-30 (02:35 UTC) = 7; dropped: promotion needed a 3-day mean >= 11.0 (base 9.5 + 1.5), i.e. days 2 + 3 >= 25 (offline it was level: thinking-off AB 11, 10 and DEV 10 = 31/99 vs base-off 30/99, agent time -12%; experiments/2026-10-30-faithful-bf-nomatch-off-AB-rerun). Both LB draws sit below every base draw but one, so the thinking-off screen did not transfer to the thinking-on LB config | 8, 7 | 2 | 7.5 | - |
| bf-t10 (candidate 4b; withdrawn 10-31 08:10, reinstated 10-31 13:00) | pub-budget-fit with temperature 1.0 / top_p 0.95 / top_k 64 (Gemma's recommended sampling) instead of 0.2 | days 1-3 queued for 11-03, 11-07, 11-11 (dated .submit_queue files, line 3 v58-t45). Reinstated because the only negative was the thinking-off proxy, which did not transfer for bf-nomatch (level offline, 8 and 7 on the LB), while new public thinking-on evidence points the other way: fabrianivan reports v19 -> v24 (byte-identical prompt and tools, only sampling 0.2 -> 1.0/0.95/64) at 0.18 -> 0.24, one draw each (experiments/variants/bf-t10/notes.md). Earlier verdict (withdrawn before any LB day: thinking-off proxy bf-t10-off AB 10/33 (base 9, 12) with verbatim repeats 13% vs ~30%, but DEV 7/33 vs base 9 and bf-nomatch 10, losing 3 easy tasks both others solved; pooled 17/66 vs ~20; experiments/2026-10-31-faithful-bf-t10-off) | - | 0 | - | - |
| bf-think2k (candidate 5) | pub-budget-fit with thinking_budget 2048 instead of 4096 (shorter thoughts: more steps per task, less 12 h runtime risk) | days 1-3 queued for 11-01, 11-05, 11-09 (dated .submit_queue files, base fallback days between, line 3 v58-t45; thinking-on, so no offline screen while the TPU lane is down). Supporting public evidence: navyadevadiga T8 (thinking_budget 256, temp 0.3, 3 tools, 8 min / 25 calls / 40 turns, Apache 2.0) scored 12 and 9 of 58 with identical files | - | 0 | - | - |
| bf-noedit (candidate 4, withdrawn 10-29) | pub-budget-fit without the edit_file tool (edits via one run_command script or write_file) | none (withdrawn before any LB day: thinking-off screen kernel v28 = 8/33 vs base twin 9/33, agent time 222 vs 220 min, output tokens/step 48.5 vs 37; data/faithful_results/bf-noedit-off-AB) | - | 0 | - | - |
| v58-t45 (conservative fallback, line 3) | prompt v5.8, thinking off, temp 0.7, 4.5 min / 40 calls / 80 turns / 180 s | 10-20 | 7 | 1 | 7.0 | none |
| v50n-t45 | prompt v5.0n, thinking off, temp 0.7, 4.5 min / 40 calls / 80 turns / 180 s | 10-05, 10-07, 10-09, 10-10, 10-13, 10-14, 10-15, 10-18, 10-19 | 6, 6, 5, 7, 6, 4, 6, 7, 5 | 9 | 5.8 | none (two Kaggle-side "system error" rescored) |
| v50n (3.5 min) | prompt v5.0n, thinking off, temp 0.7, 3.5 min / 40 calls / 80 turns | 10-08*, 10-17 | 6, 7 | 2 | 6.5 | none |
| v50n-think8 | prompt v5.0n, thinking 4096 on, 8 min / 28 calls / 80 turns / 240 s | 10-12 | 7 | 1 | 7.0 | none (finished inside 12 h) |
| v50n-t50c50 | prompt v5.0n, thinking off, 5.0 min / 50 calls / 100 turns | 10-06 | 4 | 1 | 4.0 | none |
| v47-t45 | prompt v4.7, thinking off, 4.5 min / 40 calls / 80 turns | 10-04 | 4 | 1 | 4.0 | none |
| v4.4 (submission/) | prompt v4.4, temp 0.2, thinking off; 4.5 min then 3.5 min / 40 calls | 10-01, 10-03 | fail, 4 | 1 | 4.0 | 10-01: unhandled error in the scoring run (not the 12 h cap) |
| v4.3 (submission/) | prompt v4.3, thinking off; 3.5 / 4.5 / 5.0 / 4.5 min, 30 calls / 60 turns | 09-27, 09-28, 09-29, 09-30 | 4, 6, 5, 6 | 4 | 5.25 | none |
| v3 / v4 early (submission/) | thinking medium, 10 min / 50 calls; then 5.5 min | 09-25, 09-26 | 0, fail | 1 | 0.0 | 09-26: "requested more resources than available" (capacity, not the cap) |
| sample prompt (day 1) | starter prompt, 8 min / 40 calls / 80 turns | 09-24 | 0 | 1 | 0.0 | none |
| pub-contract-first (dropped) | honghanhhh bundle: thinking 4096 on, 8 min / 28 calls / 80 turns / 240 s | 10-16 | fail | 0 | - | **"exceeded the allowed runtime" (12 h cap)**; never retried |

\* 10-08: the fallback's line-3 conservative dir (v50n at 3.5 min) went out after an unscored day, so that run is counted in the 3.5-min row, not in v50n-t45.

## Rules used by the daily routine
- The base runs on most days; a candidate gets LB days through dated files in `.submit_queue/` (since 10-31 a file
  named YYYY-MM-DD-... is eligible only from that UTC date, so a whole interleaved plan can be queued ahead; the base
  fallback fills the days between), at least 3 runs before any verdict, interleaved with base days.
- Promote a candidate to `.submit_fallback` only if its mean over >= 3 runs beats the base's mean by >= 1.5 tasks
  with no runtime failures. Drop any config on an "exceeded the allowed runtime" error and never retry it.

## Public evidence for the base family
- dariushafshar "Most-Run Public Config Averages 10/58" (census of 274 notebooks, 10-22; dataset gemma-4-agent-public-config-draws):
  6 file sets scored >= 2 times, 29 draws; pooled within-config SD 1.56 tasks (95% of single draws within +/-3.2 of
  the mean). Budget-Fit Single Agent V5 (= our pub-budget-fit, hash verified) 10.00 over 10 draws (95% CI 8.98-11.02);
  budget-aware v2 V10 (flexonafft) 9.25 over 8 (one 13, then 7, 7, 8, 9, 10, 10, 7, 9); SuperAgent V8 9.75 over 4;
  honghanhhh LB-0.24 V2 9.33 over 3 and V4 8.50 over 2. The four sets with >= 3 draws span 9.25-10.00: one draw's
  noise is wider than the whole range, so the public draws cannot rank them. The 0.24 (14-task) block has 4 teams
  with a median of 15.5 submissions; under a normal model the best of 10 identical draws sits ~2.4 tasks above the
  config's mean. Takeaway: judge by the mean over draws, run the best-mean config often, and prefer earlier
  submissions in exact ties (ties go to the earlier entry).
- (earlier, dmitriigluzdov "Public Agent Ideas and Evidence", 10-20)
- budget-fit reference files (verracodeguacas): 7 public runs solved 8-11 of 58 (mean ~10).
- budget-aware files (flexonafft prompt on the same limits): 5 runs 13, 11, 9, 7, 7 (mean ~9); the evidence
  notebook's own packaged release (same family) scored 11 (10-15) and 7 (10-19) with byte-identical files.
- Runtime: the projection at the full 8-min cap is ~15.7 h for 116 tasks, so a run fits 12 h only when most tasks
  finish early; the 12B model on the same files exceeded 12 h. Our v50n-think8 (same limits) finished; our
  pub-contract-first did not.
