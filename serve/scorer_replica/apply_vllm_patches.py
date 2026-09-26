"""Local patches to the wheelhouse vLLM 0.19.1 so the real 31B runs on a 16 GB laptop GPU under WSL2.

Run with the replica venv's python: ~/v019/bin/python serve/scorer_replica/apply_vllm_patches.py
Each patch is idempotent and keeps a .orig copy of the file it touches.
1. platforms/interface.py: allow pinned memory under WSL when VLLM_WSL_PIN=1 (measured 11.5 GiB/s pinned vs
   7.8 pageable over PCIe Gen4 x8); pinned memory also enables zero-copy UVA and the prefetch offloader.
2. v1/worker/gpu_model_runner.py: skip the assertion that forbids re-initialising the input batch when CPU
   weight offloading is on (Gemma 4's hybrid sliding/global KV cache triggers the re-init).
3. model_executor/offloader/prefetch.py: size buffers with element_size() instead of torch.finfo(), which
   rejects the packed int32 tensors of W4A16 checkpoints.
"""
import os
import shutil

import vllm

ROOT = os.path.dirname(vllm.__file__)
PATCHES = [
    ("platforms/interface.py",
     "        if in_wsl():\n            # Pinning memory in WSL is not supported.",
     "        if in_wsl() and os.environ.get(\"VLLM_WSL_PIN\") == \"1\":\n"
     "            # PATCHED (MSI): WSL2 pins memory fine for this workload (measured 11.5 GiB/s vs 7.8 pageable).\n"
     "            return True\n"
     "        if in_wsl():\n            # Pinning memory in WSL is not supported."),
    ("v1/worker/gpu_model_runner.py",
     "            assert self.offload_config.uva.cpu_offload_gb == 0, (\n"
     "                \"Cannot re-initialize the input batch when CPU weight \"\n"
     "                \"offloading is enabled. See https://github.com/vllm-project/vllm/pull/18298 \"  # noqa: E501\n"
     "                \"for more details.\"\n"
     "            )",
     "            if self.offload_config.uva.cpu_offload_gb != 0:  # PATCHED for the MSI probe: guard from PR 18298 skipped\n"
     "                logger.warning(\"PATCHED: re-initializing the input batch with CPU weight offloading enabled\")"),
    ("model_executor/offloader/prefetch.py",
     "        return numel * torch.finfo(self.dtype).bits // 8",
     "        return numel * torch.empty((), dtype=self.dtype).element_size()  # PATCHED: finfo fails on packed int32 (W4A16) weights"),
]

for rel, old, new in PATCHES:
    path = os.path.join(ROOT, rel)
    src = open(path).read()
    if "PATCHED" in src and new.splitlines()[0].strip() in src:
        print(f"already patched: {rel}")
        continue
    assert src.count(old) == 1, f"pattern not found once in {rel}"
    if not os.path.exists(path + ".orig"):
        shutil.copy(path, path + ".orig")
    src = src.replace(old, new)
    if rel == "platforms/interface.py" and "\nimport os\n" not in src:
        src = "import os\n" + src
    open(path, "w").write(src)
    print(f"patched: {rel}")
