import datetime,hashlib,json,shutil,subprocess,time
from pathlib import Path
stage=Path('/home/niko/taccomms-stage')
manifest=json.loads((stage/'manifest.json').read_text())
subprocess.run(['systemctl','stop','taccomms-screen.service'],check=True)
for name in ('screen.py','backend.py'):
    assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==manifest[name]
    shutil.copyfile(stage/name,Path('/opt/taccomms')/name)
cal=Path('/var/lib/taccomms-ui/touch.json')
if cal.exists():
    cal.rename(cal.with_name('touch.before-recalibration-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'))
subprocess.run(['systemctl','restart','taccomms-admin.service'],check=True)
subprocess.run(['systemctl','start','taccomms-screen.service'],check=True)
time.sleep(2)
print(subprocess.check_output(['systemctl','is-active','taccomms-screen.service','taccomms-admin.service','mumble-server.service'],text=True))
print('Four-target calibration is ready. Existing PINs/security state were not changed.')
