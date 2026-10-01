"""Deploy only after isolated audio and protocol checks pass; automatic rollback."""
import datetime,hashlib,json,os,py_compile,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build')
target=Path('/usr/local/lib/taccomms-noise')
dropin=Path('/etc/systemd/system/mumble-server.service.d/taccomms-noise.conf')
admin_dropin=Path('/etc/systemd/system/taccomms-admin.service.d/noise.conf')
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
api=Mumble()
try:assert len(api.users())==0,'Users connected; wait for idle before deploying.'
finally:api.ice.destroy()
integration=json.loads((base/'integration-result.json').read_text())
core=json.loads((base/'pi-core-result.json').read_text())
load=json.loads((base/'pi-load-result.json').read_text())
assert integration['passed'] and core['passed'] and load['passed']
assert integration['binary_sha256']==hashlib.sha256((base/'build/mumble-server').read_bytes()).hexdigest(),'Server binary changed after integration test.'
assert load['mean_processing_ms_per_20ms_packet']<4,'Insufficient headroom for four simultaneous speakers.'
assert not dropin.exists(),'Existing custom deployment needs an explicit update path.'
assert not target.exists(),'Existing custom deployment needs an explicit update path.'
assert not admin_dropin.exists(),'Unexpected existing audio override.'
stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
backup=Path('/var/backups/taccomms-noise')/stamp;backup.mkdir(mode=0o700,parents=True)
for path in ('/etc/mumble','/etc/systemd/system/mumble-server.service.d','/opt/taccomms/backend.py'):
    p=Path(path)
    if p.exists():
        dest=backup/path.lstrip('/');dest.parent.mkdir(parents=True,exist_ok=True)
        if p.is_dir():shutil.copytree(p,dest)
        else:shutil.copy2(p,dest)
with sqlite3.connect('/var/lib/mumble-server/mumble-server.sqlite') as source, sqlite3.connect(backup/'mumble-server.sqlite') as dest:source.backup(dest)

# Add just the reviewed audio commands to the current live backend, retaining
# the independently installed diagnostics and all existing security behavior.
backend=Path('/opt/taccomms/backend.py').read_text()
assert 'import noise_control' not in backend
backend=backend.replace('from security import SecurityStore, SecurityError','import noise_control\nfrom security import SecurityStore, SecurityError')
assert "'help': ['help [users|access|channels|system]'" in backend
backend=backend.replace("'help': ['help [users|access|channels|system]'","'help': ['help [users|access|channels|system|audio]'")
backend=backend.replace("    'users': [", "    'audio': ['noise status', 'noise on  (noise suppression + peak limiter)', 'noise off  (original audio)', 'Changes apply without disconnecting calls.'],\n    'users': [",1)
anchor="        if args == ['calibrate']:\n            return self.response(['Touch the calibration targets.'], calibrate=True)\n"
assert backend.count(anchor)==1
backend=backend.replace(anchor,anchor+"        if args in (['noise'], ['noise','status']):\n            return self.response(noise_control.status())\n        if args in (['noise','on'], ['noise','off']):\n            try:lines=noise_control.set_mode(args[1])\n            except ValueError as exc:raise SecurityError(str(exc))\n            audit('noise_mode_changed', uid=uid, mode=args[1])\n            return self.response(lines)\n")
compile(backend,'backend.py','exec');py_compile.compile(str(base/'noise_control.py'),doraise=True)
def write(path,text,mode=0o644):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name('.'+p.name+'.new');tmp.write_text(text);os.chmod(tmp,mode);os.replace(tmp,p)
def run(*args):subprocess.run(args,check=True,capture_output=True,text=True,timeout=25)

try:
    target.mkdir(mode=0o755,parents=True)
    shutil.copy2(base/'build/mumble-server',target/'mumble-server');os.chmod(target/'mumble-server',0o755)
    write('/var/lib/taccomms-audio/noise.conf','on\n')
    os.chmod('/var/lib/taccomms-audio',0o755)
    write(dropin,'[Service]\nExecStart=\nExecStart=/usr/local/lib/taccomms-noise/mumble-server -ini /etc/mumble/mumble-server.ini -fg\nEnvironment=TACCOMMS_NOISE_CONFIG=/var/lib/taccomms-audio/noise.conf\n')
    write(admin_dropin,'[Service]\nReadWritePaths=/var/lib/taccomms-audio\n')
    write('/opt/taccomms/noise_control.py',(base/'noise_control.py').read_text())
    write('/opt/taccomms/backend.py',backend)
    info={'installed_utc':stamp,'backup':str(backup),'mumble':'1.5.735-5+deb13u1',
          'rnnoise_revision':'70f1d256acd4b34a572f999a05c87bf00b67730d',
          'model_sha256':'0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37',
          'binary_sha256':hashlib.sha256((target/'mumble-server').read_bytes()).hexdigest(),
          'core_test':core,'load_test':load,'integration_test':integration,'live_headset_test_pending':True}
    write(target/'build-info.json',json.dumps(info,indent=2)+'\n')
    run('systemctl','daemon-reload');run('systemctl','restart','mumble-server');run('systemctl','restart','taccomms-admin')
    for attempt in range(20):
        try:
            api=Mumble();api.users();api.ice.destroy();break
        except Exception:
            if attempt==19:raise
            time.sleep(.5)
    run('systemctl','is-active','mumble-server','taccomms-admin','taccomms-screen')
    pid=int(subprocess.check_output(['systemctl','show','mumble-server','-p','MainPID','--value']))
    assert Path('/proc/'+str(pid)+'/exe').resolve()==target/'mumble-server'
    print('Installed central voice filter; original Debian binary retained. Backup:',backup)
except Exception:
    dropin.unlink(missing_ok=True);admin_dropin.unlink(missing_ok=True)
    shutil.copy2(backup/'opt/taccomms/backend.py','/opt/taccomms/backend.py')
    (target/'build-info.json').unlink(missing_ok=True)
    run('systemctl','daemon-reload');run('systemctl','restart','mumble-server');run('systemctl','restart','taccomms-admin')
    print('Installation failed; restored original Mumble service and admin backend.')
    raise
