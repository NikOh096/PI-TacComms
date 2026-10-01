import subprocess,sys
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
voice=Mumble()
try:print('Mumble users:',json.dumps(voice.users()))
finally:voice.ice.destroy()
for host,name,model in [('10.42.0.1','TC-HTRT01','Heltec HT-H7608-V2'),
                        ('10.42.0.160','TC-HTHD01','Heltec HT-HD01-V2'),
                        ('10.42.0.161','TC-HTHD02','Heltec HT-HD01-V2')]:
    sid=login(host,PASSWORD)
    board=rpc(host,sid,'system','board',{})
    assert board['model']==model
    configs={n:rpc(host,sid,'uci','get',{'config':n})['values'] for n in ('system','network','wireless','dhcp')}
    assert any(v.get('hostname')==name for v in configs['system'].values())
    assert configs['wireless']['default_radio0']['ssid']==name
    assert configs['wireless']['default_radio1']['ssid']=='TC-HTRT01'
    assert all(configs['wireless'][n]['key']==PASSWORD for n in ('default_radio0','default_radio1'))
    radios=rpc(host,sid,'luci-rpc','getWirelessDevices',{})
    report={'name':name,'runtime_hostname':board['hostname'],'ip':host,'admin_password_verified':True}
    report['radios']={}
    for device,radio in radios.items():
        report['radios'][device]={'up':radio.get('up'),'pending':radio.get('pending'),'interfaces':[
            {'name':i.get('ifname'),'info':{k:i.get('iwinfo',{}).get(k) for k in ('ssid','bssid','mode','country','channel','frequency','signal')}} for i in radio.get('interfaces',[])]}
    print(json.dumps(report),flush=True)
    save_backup('configured-'+name,configs)
print('Pi power:',subprocess.check_output(['vcgencmd','get_throttled'],text=True).strip())
