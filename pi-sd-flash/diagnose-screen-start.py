import json,subprocess
from pathlib import Path
for name,args in {
 'screen_log':['journalctl','-b','-u','taccomms-screen','--no-pager','-n','90'],
 'units':['systemctl','cat','taccomms-admin','taccomms-screen'],
 'clock':['timedatectl','show','-p','NTPSynchronized','-p','TimeUSec'],
 'filesystem':['findmnt','-no','OPTIONS','/'],
}.items():
    r=subprocess.run(args,capture_output=True,text=True,timeout=12)
    print(json.dumps({'check':name,'output':(r.stdout+r.stderr)[-16000:]}))
print('Existing disk logs:',[str(p) for p in Path('/var/log').glob('*') if p.name.startswith(('syslog','kern.log','messages'))])
