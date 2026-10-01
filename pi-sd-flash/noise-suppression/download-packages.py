import concurrent.futures,hashlib,json,subprocess
from pathlib import Path
base=Path(__file__).resolve().parent
dest=base/'packages';dest.mkdir(exist_ok=True)
packages=json.loads((base/'packages.json').read_text())
def fetch(p):
    path=dest/p['filename']
    assert path.parent==dest and path.name==p['filename']
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']:return path.name
    # Match APT's original HTTP transport. The expected SHA256 comes from the
    # Pi's authenticated package index; unverified bytes are never installed.
    url=p['url'].replace('https://archive.raspberrypi.com/','http://archive.raspberrypi.com/',1)
    result=subprocess.run(['curl.exe','-4','--fail','--silent','--show-error','--connect-timeout','10','--max-time','45',url],capture_output=True,timeout=50)
    if result.returncode:raise RuntimeError(path.name+': '+result.stderr.decode(errors='replace'))
    data=result.stdout
    assert len(data)==p['size'] and hashlib.sha256(data).hexdigest()==p['sha256'],path.name
    path.write_bytes(data)
    return path.name
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for name in pool.map(fetch,packages): print('Verified',name,flush=True)
