# Faithful offline evaluation on Kaggle (2026-10-03)

Problem: our T4 test runs of the real 31B could not judge prompts. Thinking was effectively on (swelite never sent
`enable_thinking: false`), FastAPI tasks ran against the wrong Pydantic (24 of 33 tasks hit import errors), and
scratch files leaked into patches. The organizers' own subprocess sandbox has related gaps on Kaggle: it inherits
the harness interpreter's site-packages (so a repro imports the image's installed rich/requests instead of
/workspace) and skips per-task dependency setup.

`kaggle/faithful_sandbox.py` patches the official swegemma 0.2.7 harness so each agent and verification sandbox is
scorer-like: a clean uv-managed CPython 3.13 venv (no host site-packages), the scorer image's base tools (pytest,
pytest-timeout 2.1.0, typer, build backends), test-only extras the public wheel set lacks, an editable install of
/workspace with dependencies resolved by pip from the multi-version competition wheels, then the dataset's
setup.py fast path (workspace .pth, pytest.ini, conftest).

Validation (`kaggle/env_check`, CPU-only kernel, official `verify_task`, 33 holdout tasks):

| attempt | gold (want 33) | null (want 0) | issue |
|---|---|---|---|
| v1 | - | - | a wheelhouse filename differs on Kaggle |
| v2 | - | - | my script passed time.time() where verify_task expects perf_counter |
| v3 | 14 | 0 | rich 10/10; requests 0/4 (no urllib3: deps live in setup.py, not pyproject); fastapi 4/19 |
| **v4** | **33** | **0** | editable install now resolves dependencies; ~11 s per verification |

Next: `kaggle/eval_faithful` runs a submission variant with the real 31B (llama.cpp, thinking off as the scorer
sends it), the official Evaluator and this sandbox, time scaled x3 for T4 speed, on a 16-task holdout subset.
