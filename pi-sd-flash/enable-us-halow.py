"""Enable the user's local U.S. HaLow AP; keep the existing LAN and credentials."""
import csv,datetime,io,json,os,time,urllib.request
from pathlib import Path
base='http://10.42.0.1'
def rpc(sid,obj,method,args):
    req=urllib.request.Request(base+'/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:result=json.load(r)
    values=result.get('result',[])
    if not values or values[0]!=0:raise RuntimeError(obj+'.'+method+' failed: '+str(values[:1] or result.get('error')))
    return values[1] if len(values)>1 else {}
sid=rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
board=rpc(sid,'system','board',{})
assert board['model']=='Heltec HT-H7608-V2'
before={name:rpc(sid,'uci','get',{'config':name})['values'] for name in ('wireless','network','dhcp')}
assert before['network']['lan']['ipaddr']=='10.42.0.1'
assert before['wireless']['radio1']['type']=='morse'
assert before['wireless']['default_radio1']['mode']=='ap'
assert before['wireless']['default_radio1']['network']=='lan'
with urllib.request.urlopen(base+'/halow-channels.csv',timeout=10) as r:table=list(csv.DictReader(io.StringIO(r.read().decode())))
selected=next(r for r in table if r['country_code']=='US' and r['s1g_chan']=='25')
assert selected['bw']=='1' and selected['centre_freq_mhz']=='914.5'
backup=Path('/var/lib/taccomms/router-backups')/('before-us-halow-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
backup.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
backup.write_text(json.dumps(before,indent=2));backup.chmod(0o600)
rpc(sid,'uci','set',{'config':'wireless','section':'radio1','values':{'disabled':'0','country':'US','channel':'25'}})
rpc(sid,'uci','set',{'config':'wireless','section':'default_radio1','values':{'disabled':'0'}})
mac='dc:a6:32:b9:ef:13'
hosts={k:v for k,v in before['dhcp'].items() if v.get('.type')=='host'}
for name,value in hosts.items():
    if value.get('ip')=='10.42.0.137' and mac not in str(value.get('mac','')).lower():
        raise RuntimeError('IP reservation conflicts with an existing host')
existing=next((name for name,value in hosts.items() if mac in str(value.get('mac','')).lower()),None)
values={'name':'halow-pi','mac':mac,'ip':'10.42.0.137','leasetime':'infinite'}
if existing:rpc(sid,'uci','set',{'config':'dhcp','section':existing,'values':values})
else:rpc(sid,'uci','add',{'config':'dhcp','type':'host','name':'taccomms_pi','values':values})
rpc(sid,'uci','apply',{'timeout':120,'rollback':True})
print('Applied U.S. channel 25 (914.5 MHz, 1 MHz); rollback pending verification.',flush=True)
deadline=time.monotonic()+65
while time.monotonic()<deadline:
    time.sleep(2)
    try:
        state=rpc(sid,'luci-rpc','getWirelessDevices',{}).get('radio1',{})
        if state.get('up') and not state.get('pending'):
            after={name:rpc(sid,'uci','get',{'config':name})['values'] for name in ('wireless','network','dhcp')}
            assert after['network']==before['network'],'Unexpected LAN configuration change'
            assert after['wireless']['radio1'].get('country')=='US'
            assert after['wireless']['radio1'].get('channel')=='25'
            rpc(sid,'uci','confirm',{})
            print('CONFIRMED: HaLow radio is up; LAN preserved; Pi reserved at 10.42.0.137.')
            print('HaLow SSID:',after['wireless']['default_radio1']['ssid'])
            print('HaLow key still factory default:',after['wireless']['default_radio1'].get('key')=='heltec.org')
            info=state.get('iwinfo',{})
            print('Runtime:',json.dumps({k:info.get(k) for k in ('country','channel','frequency','hwmodes_text')}))
            print('Backup:',backup)
            break
    except (OSError,RuntimeError) as exc:
        print('Waiting for radio startup:',type(exc).__name__,flush=True)
else:
    raise RuntimeError('Radio did not come up; rollback remains armed, no confirmation sent.')
