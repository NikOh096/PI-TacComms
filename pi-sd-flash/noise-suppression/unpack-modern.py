import hashlib,json,os,tarfile
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build')
assert os.geteuid()!=0
with tarfile.open(base/'modern-inputs.tar.gz') as archive:
    archive.extractall(base,filter='data')
for name,digest in json.loads((base/'modern-inputs.json').read_text()).items():
    p=(base/name).resolve()
    assert p.is_relative_to(base) and hashlib.sha256(p.read_bytes()).hexdigest()==digest,name
print('Modern source bundle extracted and all file hashes verified.')
