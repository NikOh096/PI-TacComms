"""Install diagnostics and the narrow screen startup fix; leave Mumble untouched."""
import datetime,hashlib,json,os,py_compile,shutil,subprocess,time
from pathlib import Path
stage=Path('/home/niko/taccomms-diagnostics-stage')
backup=Path('/var/backups/taccomms-diagnostics')/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
backup.mkdir(mode=0o700,parents=True,exist_ok=False)
paths=['/opt/taccomms/client.py','/opt/taccomms/screen.py','/opt/taccomms/backend.py',
       '/etc/systemd/journald.conf.d/99-taccomms-persistent.conf',
       '/etc/systemd/system/taccomms-admin.service.d/diagnostics.conf',
       '/etc/systemd/system/taccomms-diagnostics.service',
       '/usr/local/lib/taccomms-diagnostics/monitor.py']
manifest={}
for name in paths:
    p=Path(name)
    if p.exists():
        out=backup/name.lstrip('/');out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,out)
        manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
    else:manifest[name]=None
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

def install(text,path,mode=0o644):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name('.'+p.name+'.diagnostics-new')
    tmp.write_text(text);os.chmod(tmp,mode);os.replace(tmp,p)

for name in ('monitor.py','client.py'):
    py_compile.compile(str(stage/name),doraise=True)

# Patch only the verified live startup call and diagnostic commands. The staged
# noise suppression prototype is deliberately not installed by this operation.
screen=Path('/opt/taccomms/screen.py').read_text()
if 'from client import request, wait_ready' not in screen:
    assert screen.count('from client import request\n')==1
    assert screen.count("\n            self.state=self.call('state')\n")==1
    screen=screen.replace('from client import request\n','from client import request, wait_ready\n')
    screen=screen.replace("\n            self.state=self.call('state')\n",'\n            self.state=wait_ready()\n')
backend=Path('/opt/taccomms/backend.py').read_text()
if "if args in (['health'], ['crashlog']):" not in backend:
    old="    'system': ['status', 'network', 'processes', 'logs [1..100]', 'audit [1..100]',"
    assert backend.count(old)==1
    backend=backend.replace(old,"    'system': ['status', 'health', 'crashlog  (save diagnostic report)', 'network', 'processes', 'logs [1..100]', 'audit [1..100]',")
    anchor="        if args == ['calibrate']:\n            return self.response(['Touch the calibration targets.'], calibrate=True)\n"
    assert backend.count(anchor)==1
    backend=backend.replace(anchor,anchor+"        if args in (['health'], ['crashlog']):\n            command=['/usr/bin/python3','/usr/local/lib/taccomms-diagnostics/monitor.py']\n            if args==['health']:command.append('--brief')\n            return self.response(run(*command,timeout=30).splitlines())\n")
compile(screen,'screen.py','exec');compile(backend,'backend.py','exec')
install((stage/'monitor.py').read_text(),'/usr/local/lib/taccomms-diagnostics/monitor.py')
install((stage/'client.py').read_text(),'/opt/taccomms/client.py')
install(screen,'/opt/taccomms/screen.py');install(backend,'/opt/taccomms/backend.py')
install((stage/'taccomms-diagnostics.service').read_text(),'/etc/systemd/system/taccomms-diagnostics.service')
install('[Service]\nReadWritePaths=/var/lib/taccomms-diagnostics\n','/etc/systemd/system/taccomms-admin.service.d/diagnostics.conf')
install('[Journal]\nStorage=persistent\nSystemMaxUse=128M\nSystemKeepFree=512M\nSystemMaxFileSize=16M\nMaxRetentionSec=14day\nSyncIntervalSec=30s\nCompress=yes\n','/etc/systemd/journald.conf.d/99-taccomms-persistent.conf')
Path('/var/lib/taccomms-diagnostics').mkdir(mode=0o700,exist_ok=True)

def run(*args):subprocess.run(args,check=True)
run('systemctl','daemon-reload')
run('systemd-tmpfiles','--create','--prefix=/var/log/journal')
run('systemctl','restart','systemd-journald')
run('journalctl','--flush');run('journalctl','--sync')
# Restart just the UI/admin services. Calls and the server continue running.
run('systemctl','restart','taccomms-admin','taccomms-screen')
run('systemctl','enable','--now','taccomms-diagnostics')
print('Installed persistent diagnostics. Backup:',backup)
