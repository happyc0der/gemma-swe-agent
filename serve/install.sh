#!/bin/bash
export PATH="$HOME/.local/bin:$PATH"
cd ~/Projects/gemma-swe-agent/serve
uv pip install --python .venv/bin/python vllm huggingface_hub > install.log 2>&1
echo "VLLM_INSTALL_DONE rc=$?" >> install.log
