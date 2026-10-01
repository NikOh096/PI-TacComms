import hashlib,json,shutil,subprocess,time
from pathlib import Path
stage=Path('/home/niko/taccomms-stage')
manifest=json.loads((stage/'manifest.json').read_text())
assert hashlib.sha256((stage/'screen.py').read_bytes()).hexdigest()==manifest['screen.py']
shutil.copyfile(stage/'screen.py','/opt/taccomms/screen.py')
subprocess.run(['systemctl','restart','taccomms-screen.service'],check=True)
time.sleep(3)
print(subprocess.check_output(['journalctl','-u','taccomms-screen.service','-n','10','--no-pager','-o','cat'],text=True))
print('Saved PINs, calibration and Mumble service unchanged.')
