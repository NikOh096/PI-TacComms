import subprocess,sys
host='10.42.0.1';sid=login(host,PASSWORD)
assert rpc(host,sid,'system','board',{})['hostname']=='TC-HTRT01'
before=rpc(host,sid,'uci','get',{'config':'dhcp'})['values']
save_backup('before-tc-reservations',{'dhcp':before})
for section,name,mac,address in [('taccomms_hd01','TC-HTHD01','e4:38:19:2a:bf:d0','10.42.0.160'),
                                ('taccomms_hd02','TC-HTHD02','e4:38:19:2a:a0:4e','10.42.0.161')]:
    for key,value in before.items():
        if value.get('.type')=='host' and value.get('ip')==address:
            assert mac in str(value.get('mac','')).lower(),'Conflicting DHCP reservation'
    values={'name':name,'mac':mac,'ip':address,'leasetime':'infinite'}
    if section in before:rpc(host,sid,'uci','set',{'config':'dhcp','section':section,'values':values})
    else:rpc(host,sid,'uci','add',{'config':'dhcp','type':'host','name':section,'values':values})
rpc(host,sid,'uci','apply',{'timeout':90,'rollback':True})
for address in ('10.42.0.160','10.42.0.161'):
    fresh=login(address,PASSWORD)
    assert rpc(address,fresh,'system','board',{})['model']=='Heltec HT-HD01-V2'
rpc(host,sid,'uci','confirm',{})
print('Gateway reservations verified: TC-HTHD01=10.42.0.160, TC-HTHD02=10.42.0.161; Pi=10.42.0.137.',flush=True)
after={n:rpc(host,sid,'uci','get',{'config':n})['values'] for n in ('system','network','wireless','dhcp')}
save_backup('configured-TC-HTRT01',after)
subprocess.run(['systemctl','daemon-reload'],check=True)
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
m=Mumble()
try:print('Connected users:',json.dumps(m.users()))
finally:m.ice.destroy()
print('Pi power:',subprocess.check_output(['vcgencmd','get_throttled'],text=True).strip())
