# Real 31B on Kaggle T4x2 (llama.cpp, official QAT Q4_0 GGUF), day-3 config, 33 holdout tasks

Kernel: `kaggle/eval_31b_llamacpp/run.py` (dankaxon/gemma4-31b-holdout-eval). Versions 1-4 fixed the data path, Kaggle's missing venv module, a swelite path-rewrite bug, and a silent server death.
v5 (16k per slot, watchdog): **1/33 resolved (requests_7309)**, but the server was SIGKILLed 11 times (rc=-9, every 3-5 min): 22 tasks died on ServiceUnavailable, 7 on InternalServerError, only 4 reached a budget end. Mean 5.6 calls/task, 7 non-empty patches, 0 explicit submits. Cause: the memory-mapped 17.6 GB model's page cache counts against Kaggle's 30 GB container limit. Even so, the 31B produced a correct fix end to end once, so tool calling, editing and patch extraction work with the real model.
Throughput seen: prompt eval 70-165 tok/s, generation 6-8 tok/s per slot with two slots.
v6: `--no-mmap` plus memory logging.
