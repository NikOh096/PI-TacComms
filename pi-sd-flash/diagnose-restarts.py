import json,subprocess
from pathlib import Path
checks={
 'boot_history':['journalctl','--list-boots','--no-pager'],
 'journal_storage':['journalctl','--disk-usage'],
 'previous_kernel':['journalctl','-k','-b','-1','--no-pager','-n','70'],
 'previous_shutdown':['journalctl','-b','-1','--no-pager','-n','45'],
 'current_kernel':['journalctl','-k','-b','--no-pager','-p','warning','-n','65'],
 'power':['vcgencmd','get_throttled'],
 'temperature':['vcgencmd','measure_temp'],
 'services':['systemctl','show','mumble-server','taccomms-admin','taccomms-screen','-p','Id','-p','ActiveState','-p','SubState','-p','NRestarts','-p','Result'],
 'logging_config':['systemd-analyze','cat-config','systemd/journald.conf'],
 'disk':['df','-h','/','/var/log'],
}
for name,args in checks.items():
    r=subprocess.run(args,capture_output=True,text=True,timeout=15)
    print(json.dumps({'check':name,'rc':r.returncode,'output':(r.stdout+r.stderr)[-18000:]}),flush=True)
print(json.dumps({'pstore_files':[p.name for p in Path('/sys/fs/pstore').glob('*')],
 'journal_persistent_dir':Path('/var/log/journal').exists(),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
