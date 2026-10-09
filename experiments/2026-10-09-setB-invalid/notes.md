# Set B run of 2026-10-09 (kernel v10): INVALID, server build changed

v5.0n 0/17 and v5.2 2/17 on the 17 unused holdout tasks, but every task hit the 10.5-min session timeout after only
6-23 calls. Cause: output length, not task difficulty. Median output tokens per step were 250 (v5.0n) and 283 (v5.2)
versus ~35 in every earlier run; one `sed -n` call took 4,259 tokens. Generation speed itself was normal (~12 tok/s).

The kernel cloned llama.cpp HEAD on every run. Between the normal set-A runs (10-08, last at upstream 71ad0590f) and
this one (cloned 10-09 14:32), upstream merged CUDA MMQ precision changes and "keep the backend sampling graph static
across ubatches" (14:20, 12 minutes before the clone). The thinking checks passed (the server still refused to think
on a trivial prompt), so they did not catch it.

Fixes (kernel v11): llama.cpp pinned to 71ad0590f4808b6202f9213d166913858c73b1bc; a canary task (fastapi_14303, solved
in 4-7 calls by every normal run) must be resolved with median output <= 120 tokens per step or the kernel stops.
~6.6 GPU h lost.
