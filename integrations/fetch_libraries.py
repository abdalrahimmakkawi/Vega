"""Fetch upstream archives, preserve licenses, record exact commit revisions."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
REPOS={'PicoGK':'PicoGK','ShapeKernel':'LEAP71_ShapeKernel',
       'LatticeLibrary':'LEAP71_LatticeLibrary','QuasiCrystals':'LEAP71_QuasiCrystals'}

def fetch(item):
    name,repo=item
    request=urllib.request.Request(f'https://api.github.com/repos/leap71/{repo}/commits/main',headers={'User-Agent':'Vega-local-research'})
    revision=json.load(urllib.request.urlopen(request,timeout=30))['sha']
    raw=urllib.request.urlopen(f'https://codeload.github.com/leap71/{repo}/zip/{revision}',timeout=90).read()
    destination=ROOT/'vendor'/name
    if destination.exists():
        raise RuntimeError(f'{destination} already exists; preserve it or move it before fetching.')
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        for member in archive.infolist():
            relative=Path(*Path(member.filename).parts[1:])
            target=(destination/relative).resolve()
            if not target.is_relative_to(destination.resolve()):raise ValueError('Unsafe archive path')
            if member.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(archive.read(member))
    return name,{'repository':f'https://github.com/leap71/{repo}','commit':revision,'archive_sha256':hashlib.sha256(raw).hexdigest()}

if __name__=='__main__':
    lock=ROOT/'vendor'/'libraries.lock.json'
    records=json.loads(lock.read_text()) if lock.exists() else {}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name,record in pool.map(fetch,[(k,v) for k,v in REPOS.items() if k not in records]):
            records[name]=record
            lock.write_text(json.dumps(records,indent=2))
            print(name,record['commit'])
