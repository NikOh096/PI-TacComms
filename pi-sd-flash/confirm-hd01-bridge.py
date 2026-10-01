# SESSION is supplied in memory by the task-scoped deployment wrapper.
import json,time,urllib.request
from pathlib import Path
def rpc(host,sid,obj,method,args):
    req=urllib.request.Request('http://'+host+'/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5) as r:value=json.load(r)
    result=value.get('result',[])
    if not result or result[0]!=0:raise RuntimeError(obj+'.'+method+' failed')
    return result[1] if len(result)>1 else {}
gateway=rpc('10.42.0.1','0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
deadline=time.monotonic()+80
while time.monotonic()<deadline:
    time.sleep(2)
    try:
        leases=rpc('10.42.0.1',gateway,'luci-rpc','getDHCPLeases',{}).get('dhcp_leases',[])
        matches=[v for v in leases if 'bfd0' in v.get('hostname','').lower() or v.get('macaddr','').lower().endswith('2a:bf:d0')]
        if not matches:continue
        address=matches[0]['ipaddr']
        board=rpc(address,SESSION,'system','board',{})
        assert board.get('model')=='Heltec HT-HD01-V2' and board.get('hostname')=='HT-HD01-BFD0'
        network=rpc(address,SESSION,'uci','get',{'config':'network'})['values']
        wireless=rpc(address,SESSION,'uci','get',{'config':'wireless'})['values']
        dhcp=rpc(address,SESSION,'uci','get',{'config':'dhcp'})['values']
        assert network['lan']['proto']=='dhcp'
        assert wireless['default_radio1']['network']=='lan' and wireless['default_radio1']['ssid']=='WHL-AP-72AA'
        assert dhcp['lan']['ignore']=='1'
        rpc(address,SESSION,'uci','confirm',{})
        record={'ip':address,'hostname':board['hostname'],'confirmed':True,'time':time.time()}
        Path('/var/lib/taccomms/hd01-pairing.json').write_text(json.dumps(record))
        print('CONFIRMED: HD01 connected over HaLow in bridge mode. Management address:',address)
        print('Gateway DHCP supplies addresses; local HD01 DHCP disabled.')
        break
    except (OSError,RuntimeError,KeyError):continue
else:raise RuntimeError('Bridge not verified; rollback remains armed. No confirmation sent.')
