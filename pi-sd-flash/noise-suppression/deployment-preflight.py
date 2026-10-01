import json,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
print('Active Mumble users:',len(Mumble().users()))
for name,args in {
 'unit':['systemctl','cat','mumble-server'],
 'runtime':['systemctl','show','mumble-server','-p','Type','-p','ExecStart','-p','User','-p','Group','-p','MainPID'],
 'filesystem':['findmnt','-no','OPTIONS','/'],
}.items():
    r=subprocess.run(args,capture_output=True,text=True,timeout=15)
    print(json.dumps({'check':name,'output':r.stdout+r.stderr}))
print('Database candidates:',[str(p) for p in Path('/var/lib/mumble-server').glob('*') if p.is_file()])
print('Existing custom filter:',Path('/usr/local/lib/taccomms-noise/build-info.json').exists())
