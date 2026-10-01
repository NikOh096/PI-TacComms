import hashlib,json,shutil,subprocess,time
from pathlib import Path
stage=Path('/home/niko/taccomms-stage')
for name,digest in json.loads((stage/'manifest.json').read_text()).items():
    assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest
    if name.endswith('.py'): shutil.copyfile(stage/name,Path('/opt/taccomms')/name)
subprocess.run(['systemctl','disable','--now','halow-console.service'],check=True)
subprocess.run(['systemctl','enable','--now','taccomms-screen.service'],check=True)
time.sleep(3)
print(subprocess.check_output(['systemctl','show','taccomms-screen.service','-p','ActiveState','-p','SubState','-p','MainPID'],text=True))
print(subprocess.check_output(['journalctl','-u','taccomms-screen.service','-n','15','--no-pager','-o','cat'],text=True))
