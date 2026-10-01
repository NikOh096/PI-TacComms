import os,shutil,subprocess,sys,time
from pathlib import Path
source=Path('/home/niko/taccomms-diagnostics-stage/monitor.py')
compile(source.read_text(),str(source),'exec')
shutil.copyfile(source,'/usr/local/lib/taccomms-diagnostics/monitor.py')
os.chmod('/usr/local/lib/taccomms-diagnostics/monitor.py',0o644)
clock=Path('/var/lib/systemd/timesync/clock')
if clock.exists():
    os.utime(clock,None)
    print('Saved corrected clock floor for subsequent offline boots.')
subprocess.run(['systemctl','restart','taccomms-diagnostics'],check=True)
time.sleep(1)
subprocess.run(['python3','/usr/local/lib/taccomms-diagnostics/monitor.py'],check=True)
subprocess.run(['journalctl','--sync'],check=True)
