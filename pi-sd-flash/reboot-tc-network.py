import sys
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
voice=Mumble()
try:
    users=voice.users()
    assert len(users)<2,'Multiple voice users connected; stop before network restart.'
finally:voice.ice.destroy()
for host,name in [('10.42.0.160','TC-HTHD01'),('10.42.0.161','TC-HTHD02'),('10.42.0.1','TC-HTRT01')]:
    sid=login(host,PASSWORD)
    system=rpc(host,sid,'uci','get',{'config':'system'})['values']
    assert any(v.get('hostname')==name for v in system.values())
    try:rpc(host,sid,'system','reboot',{})
    except OSError:pass
    print('Restart requested:',name,flush=True)
