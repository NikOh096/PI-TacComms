import hashlib,json,subprocess,tarfile,shutil
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build')
with tarfile.open(base/'build-inputs.tar') as archive:
    archive.extractall(base,filter='data')
packages=json.loads((base/'packages.json').read_text())
paths=[]
for p in packages:
    path=base/'packages'/p['filename']
    assert path.parent==base/'packages'
    assert path.stat().st_size==p['size']
    assert hashlib.sha256(path.read_bytes()).hexdigest()==p['sha256']
    paths.append(str(path))
    shutil.copy2(path,Path('/var/cache/apt/archives')/path.name)
print('All offline package checksums verified.',flush=True)
subprocess.run(['apt-get','install','-y','--no-download','--no-remove','--no-install-recommends',
    *[p['filename'].split('_')[0] for p in packages]],check=True)
print('BUILD DEPENDENCIES READY; no server restart requested.',flush=True)
