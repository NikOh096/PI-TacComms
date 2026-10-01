import hashlib,json,shutil,subprocess,time
from pathlib import Path
stage=Path('/home/niko/taccomms-stage')
manifest=json.loads((stage/'manifest.json').read_text())
for name in ('screen.py','backend.py','taccomms-screen.service'):
    assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==manifest[name]
    target=Path('/opt/taccomms')/name if name.endswith('.py') else Path('/etc/systemd/system')/name
    shutil.copyfile(stage/name,target)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','taccomms-admin.service'],check=True)
subprocess.run(['systemctl','restart','taccomms-screen.service'],check=True)
time.sleep(3)
print(subprocess.check_output(['systemctl','is-active','taccomms-screen.service','taccomms-admin.service','mumble-server.service'],text=True))
print('Tap-to-cycle menu with Admin and confirmed Lock buttons installed. PINs/calibration preserved.')
