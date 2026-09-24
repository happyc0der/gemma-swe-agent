#!/bin/bash
cd ~/Projects/gemma-swe-agent/data/competition
python3 - > ../unzip.log 2>&1 <<'PY'
import zipfile, os
z=zipfile.ZipFile('/mnt/c/Users/keshav/gemma-4-developer-agent.zip')
names=[n for n in z.namelist() if n.split('/')[0] in ('snapshots','graphs','embeddings') and not os.path.exists(n)]
for i,n in enumerate(names,1):
    z.extract(n,'.')
    if i%50==0: print(i,'/',len(names),flush=True)
print('UNZIP_DONE', len(os.listdir('snapshots')), len(os.listdir('graphs')), len(os.listdir('embeddings')))
PY
