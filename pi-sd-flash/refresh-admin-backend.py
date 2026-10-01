import hashlib,json,shutil,subprocess
from pathlib import Path
stage=Path('/home/niko/taccomms-stage')
manifest=json.loads((stage/'manifest.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest
    target=Path('/opt/taccomms')/name if name.endswith('.py') else Path('/etc/systemd/system')/name
    shutil.copyfile(stage/name,target)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','taccomms-admin.service'],check=True)
print('Updated backend; voice server untouched.')
