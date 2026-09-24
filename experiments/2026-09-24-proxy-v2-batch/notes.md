# Proxy batch: prompt v2, Gemma 4 12B (Ollama, 32k ctx, thinking off), 4 tasks, 12 min / 40 calls

Result: 0/4 resolved. requests_7205: 40 calls, repeated `python3 -c` repro one-liners, submit with empty patch. rich_2725: 9 calls then a >10 min model stall. rich_3454: found the right regex line, 8 identical failed edit_file calls (anchor had backslash-escaped quotes not present in the file), empty submit. fastapi_11355: repeated the same heredoc repro 8 times, no edit.

Taxonomy: no_patch 4 (2 x repetition loop, 1 x edit_mismatch from escaped quotes, 1 x budget/stall).
What worked: heredoc reproduction (no more shell-quoting loops), tight tool loop without nudges, explicit submit_patch.
Decisions: v3 adds loop-escape rules and a scripted edit fallback. The Mac proxy without thinking is a mechanics check only; real prompt tuning needs the 31B with thinking (Kaggle T4x2) or the 12B with thinking on the MSI GPU.
