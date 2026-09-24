$env:OLLAMA_HOST = '0.0.0.0:11435'
$env:OLLAMA_NUM_PARALLEL = '2'
$env:OLLAMA_KEEP_ALIVE = '2h'
& 'C:\Users\KESHAV\AppData\Local\Programs\Ollama\ollama.exe' serve *> 'C:\Users\keshav\ollama_serve.log'
