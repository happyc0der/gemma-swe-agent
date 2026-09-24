#!/bin/bash
/mnt/c/Users/KESHAV/AppData/Local/Programs/Ollama/ollama.exe pull gemma4:12b > ~/Projects/gemma-swe-agent/serve/ollama_pull.log 2>&1
echo "OLLAMA_PULL_DONE rc=$?" >> ~/Projects/gemma-swe-agent/serve/ollama_pull.log
