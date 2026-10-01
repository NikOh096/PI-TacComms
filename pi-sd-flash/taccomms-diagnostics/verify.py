import json,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from backend import Admin
import backend
from security import SecurityStore,SecurityError
backend.audit=lambda *a,**k:None
with tempfile.TemporaryDirectory(prefix='verify-',dir='/var/lib/taccomms-diagnostics') as temp:
    security=SecurityStore(temp)
    security.enroll('284691','284691','739205','739205')
    admin=Admin(mumble=object(),security=security)
    for cmd in ('health','crashlog'):
        try:admin.dispatch({'op':'command','line':cmd},1000,1000)
        except SecurityError:pass
        else:raise AssertionError('Unauthenticated diagnostics allowed')
    token=security.login('284691',1000)
    result=admin.dispatch({'op':'command','line':'health','token':token},1000,1000)
    assert any('Power:' in line for line in result['lines'])
    security.emergency()
    try:admin.dispatch({'op':'command','line':'health','token':token},1000,1000)
    except SecurityError:pass
    else:raise AssertionError('Emergency lock bypassed')
print('PASS: diagnostic admin commands require login and respect emergency lock.')
for args in [ ['systemctl','show','mumble-server','taccomms-admin','taccomms-screen','taccomms-diagnostics','-p','Id','-p','ActiveState','-p','NRestarts','-p','MainPID'],
 ['journalctl','-u','taccomms-diagnostics','-n','15','--no-pager'],
 ['journalctl','-b','-u','taccomms-screen','--since','-3min','--no-pager','-n','24'],
 ['journalctl','--disk-usage'] ]:
    print(subprocess.run(args,capture_output=True,text=True).stdout)
data=Path('/var/lib/taccomms-diagnostics')
print('Persistent journals:',[p.name for p in Path('/var/log/journal').glob('*/*.journal')])
print('Latest sample:',(data/'last-state.json').read_text())
print('Snapshot:',(data/'latest-report.json').exists())
