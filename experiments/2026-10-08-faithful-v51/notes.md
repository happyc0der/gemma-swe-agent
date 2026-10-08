# Faithful eval: prompt v5.1 vs v5.0n (same 16 holdout tasks)

Kernel v8, 14:11-16:45 UTC, 118 min of agent runs, 2.5 GPU h. v5.1 = v5.0n + (1) sibling check printing lines with
`grep -n` on the exact changed expression, (2) at most 3 probes before the first edit, (3) call get_status after ~12
calls and edit if nothing is edited yet.

| metric | v5.0n | v5.1 |
|---|---|---|
| solved | 9 | 8 (gained rich_3480; lost fastapi_12942, requests_6644) |
| exact repeat calls | 51 | 135 |
| session timeouts | 1 | 1 |
| median call of first edit | 16 | 13 |
| agent time | 112 min | 118 min |

- The sibling rule works: rich_3480 (fix `append` and its twin `append_text`) is solved for the first time.
- The probe cap and the get_status checkpoint were ignored (get_status called once in the whole run; requests_7427
  repeated one `python3 -c` probe 12 times).
- requests_6644 was lost to the malformed-call loop again: 35 identical rejected `edit_file` calls whose
  `new_string` held a docstring (`\"\"\"`), which broke the call format so `old_string` was swallowed. The "never
  resend it" rule in v5.0n does not stop the loop once it starts; across runs this loop hit v4.7 (11 calls), v4.9
  (41), v5.1 (35). The fix has to act before the call is written.

Next: v5.2 = v5.0n + the sibling rule + "code with triple quotes or backticks goes through /tmp/fix.py, not edit_file"
(and the fix.py template uses ''' when the code contains \"\"\"). The two ignored rules are dropped.
