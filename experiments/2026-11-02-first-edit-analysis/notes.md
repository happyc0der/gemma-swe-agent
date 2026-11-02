# First-edit timing vs resolution in the base's thinking-off traces (2026-11-02)

Prompted by leoprovorov's public notebook "Single Agent Anytime Patch" (run 11-01, unscored on the LB), which counts
Dmitrii Gluzdov's 692 local runs (CC BY 4.0): 28% ended with no patch at all; for the thinking-on `v4` config, runs
that finished within 14 tool calls resolved 52% (37/71) and runs that went on to 15-20 calls resolved 5% (2/43).

Same tabulation over our 99 official-harness tasks of pub-budget-fit with thinking off (AB 9/33, AB rerun 12/33,
DEV 9/33; `scripts/faithful_metrics.py` task_metrics, first edit = first edit_file / write_file / fix-script call):

| first source edit at call | tasks | solved |
|---|---|---|
| never | 17 | 0 (0%) |
| 1-8 | 33 | 21 (64%) |
| 9-12 | 4 | 3 (75%) |
| 13-20 | 18 | 4 (22%) |
| 21+ | 27 | 2 (7%) |

| total tool calls in the task | tasks | solved |
|---|---|---|
| <= 14 | 18 | 14 (78%) |
| 15-28 | 63 | 16 (25%) |
| > 28 (80-turn loops) | 18 | 0 (0%) |

Reading:
- The base prompt already says "By your 12th tool call you must have edited a source file" and "Do NOT conclude
  without submitting a non-empty patch", yet the median first edit is call 17-20 and 45 of 99 tasks edit after call
  12 or never. The rule is stated and not obeyed, like the budget-warning bullet (bf-warn: followed 3/23) and the
  edit-fallback bullet (bf-editfb: 6/236). Moving the number from 12 to 8 in the prompt (leoprovorov's edit 1) is
  therefore not a candidate for us without a different delivery mechanism.
- The correlation is partly selection: easy tasks get edited early. It still says where the misses are: 17 never-edit
  tasks and 27 very-late edits are 44% of the set and contribute 2 solves.
- Nothing here changes an LB decision today; it goes into the paper's failure taxonomy (Section 4) with credit to
  leoprovorov and Gluzdov, and is the evidence base if a third candidate on "first edit earlier" is built on 11-04/05.
