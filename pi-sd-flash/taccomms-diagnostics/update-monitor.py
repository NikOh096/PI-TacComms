import datetime,os,shutil,subprocess,time
from pathlib import Path
source=Path('/home/niko/taccomms-diagnostics-stage/monitor.py')
target=Path('/usr/local/lib/taccomms-diagnostics/monitor.py')
compile(source.read_text(),str(source),'exec')
backup=Path('/var/backups/taccomms-diagnostics')/('monitor-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'.py')
shutil.copy2(target,backup);os.chmod(backup,0o600)
temporary=target.with_name('monitor.new.py');shutil.copyfile(source,temporary);os.chmod(temporary,0o644);os.replace(temporary,target)
subprocess.run(['systemctl','restart','taccomms-diagnostics'],check=True)
time.sleep(1)
subprocess.run(['systemctl','is-active','taccomms-diagnostics'],check=True)
subprocess.run(['python3',str(target),'--brief'],check=True)
print('Diagnostics updated to avoid repeatedly starting the clock-management service.')
