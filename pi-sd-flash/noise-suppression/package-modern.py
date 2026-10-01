"""Create a minimal source bundle for the isolated Pi build, no model training files."""
import hashlib,json,tarfile
from pathlib import Path
base=Path(__file__).resolve().parent
upstream=base/'inspect/rnnoise-70f1d256acd4b34a572f999a05c87bf00b67730d'
assert hashlib.sha256((base/'rnnoise-modern-model.tar.gz').read_bytes()).hexdigest()=='0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37'
files=[base/name for name in ('TacCommsDenoiser.cpp','TacCommsDenoiser.h','test-filter.cpp','patch-source.py','build.py','modern-rnnoise.cmake')]
files += [upstream/name for name in ('COPYING','AUTHORS','README','model_version')]
files += list((upstream/'include').glob('*.h'))
files += [p for p in (upstream/'src').rglob('*') if p.is_file() and p.suffix in ('.c','.h')]
manifest={str(p.relative_to(base)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(base/'modern-inputs.json').write_text(json.dumps(manifest,indent=2)+'\n')
with tarfile.open(base/'modern-inputs.tar.gz','w:gz') as archive:
    for p in files+[base/'modern-inputs.json']:
        archive.add(p,arcname=p.relative_to(base),recursive=False)
print('Source bundle:',(base/'modern-inputs.tar.gz').stat().st_size,'bytes; files:',len(files))
