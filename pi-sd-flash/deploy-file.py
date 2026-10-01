"""Build an integrity-checked SSH deployment script without shell interpolation."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import sys

base = Path(__file__).resolve().parent
source = Path(sys.argv[1])
targets = sys.argv[2:]
data = source.read_bytes()
script = base / 'deploy-current.py'
script.write_text('''import base64, hashlib, os
from pathlib import Path
data = base64.b64decode(%r)
assert hashlib.sha256(data).hexdigest() == %r
for name in %r:
    path = Path(name)
    original = path.with_name(path.name + '.before-repair')
    if path.exists() and not original.exists():
        original.write_bytes(path.read_bytes())
    path.write_bytes(data)
    path.chmod(0o755 if name.startswith('/usr/local/bin/') else 0o644)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == %r
    manifest = path.parent / 'BUNDLE-SHA256SUMS'
    if manifest.exists():
        lines = manifest.read_text().splitlines()
        lines = [%r + '  ' + path.name if line.endswith('  ' + path.name) else line for line in lines]
        manifest.write_text('\\n'.join(lines) + '\\n')
    print('Deployed and verified:', name)
os.sync()
''' % (base64.b64encode(data).decode(), hashlib.sha256(data).hexdigest(), targets,
       hashlib.sha256(data).hexdigest(), hashlib.sha256(data).hexdigest()), encoding='utf-8')
sys.exit(subprocess.run([sys.executable, str(base/'pi-admin.py'), str(script), '--python']).returncode)
