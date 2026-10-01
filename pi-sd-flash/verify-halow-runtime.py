import json,urllib.request
def rpc(sid,obj,method,args):
    req=urllib.request.Request('http://10.42.0.1/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:value=json.load(r)
    result=value.get('result',[])
    assert result and result[0]==0,value.get('error')
    return result[1] if len(result)>1 else {}
sid=rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
radio=rpc(sid,'luci-rpc','getWirelessDevices',{})['radio1']
print('Radio state:',{k:radio.get(k) for k in ('up','pending','disabled','retry_setup_failed')})
for item in radio.get('interfaces',[]):
    info=item.get('iwinfo',{})
    print('Interface:',item.get('ifname'),{k:info.get(k) for k in ('ssid','bssid','country','channel','frequency','txpower','mode')})
    print('Associated stations:',len(item.get('stations',[])))
print('Reserved Pi:',rpc(sid,'uci','get',{'config':'dhcp','section':'taccomms_pi'}))
