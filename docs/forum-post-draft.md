# Draft forum post (not published; needs Keshav's OK)

**Title:** read_file line ranges always fail under the released harness: ADK 1.36.1 sends `any_of` / `INTEGER` tool schemas

Running my submission through the wheelhouse packages (swegemma 0.2.7, google-adk 1.36.1) against a local vLLM
Gemma 4 server, every `read_file(filepath, start_line, end_line)` call errors with
`'>' not supported between instances of 'int' and 'str'`. The official `sample_submission` prompt hits it too
(17 of 22 read_file calls failed in one task).

Cause: google-adk 1.36.1's LiteLlm converter serializes optional parameters as
`{"any_of": [{"type": "INTEGER"}, {"type": "NULL"}], "nullable": true}` (snake_case `any_of`, Gemini-style upper-case
type names) in the OpenAI `tools` payload. The Gemma 4 chat template renders that schema, the model then emits the
numbers as quoted strings, vLLM's gemma4 parser keeps them as strings, and neither ADK nor swegemma coerces them.
With google-adk 2.9.2, which emits `anyOf` / `integer`, the same model and server return integers and the tool works.

Probe (same server, same prompt "show me lines 10 to 20 of fastapi/params.py"):
- ADK 1.36.1: tools payload has `"start_line": {"any_of": [{"type": "INTEGER"}, {"type": "NULL"}], "nullable": true}`; function receives `'10'`, `'20'` (str).
- ADK 2.9.2: tools payload has `"start_line": {"anyOf": [{"type": "integer"}, {"type": "null"}]}`; function receives `10`, `20` (int).

The same applies to any non-string tool parameter (`allow_multiple`, `k`, `max_neighbors`, the `nodes` list).

Workarounds for participants until the scorer's ADK is fixed: don't expose `read_file` (read with `sed -n 'A,Bp'`
via run_command), never pass `allow_multiple`, `k` or `max_neighbors`, avoid `get_code_subgraph`.

Suggested fix on the organizer side: have swegemma's tools coerce arguments to their annotated types, or upgrade the
pinned google-adk (the fix is in the `_schema_to_dict` path of `google/adk/models/lite_llm.py`).
