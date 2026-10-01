import datetime,json,os,urllib.request
from pathlib import Path
base='http://10.42.0.1'
def rpc(session,obj,method,args):
    payload=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[session,obj,method,args]}).encode()
    req=urllib.request.Request(base+'/ubus',data=payload,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=12) as response: value=json.load(response)
    result=value.get('result',[])
    if not result or result[0]!=0: raise RuntimeError(obj+'.'+method+' returned '+str(result[:1]))
    return result[1] if len(result)>1 else {}
session=rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
snapshot={name:rpc(session,'uci','get',{'config':name})['values'] for name in ('wireless','network','dhcp')}
dest=Path('/var/lib/taccomms/router-backups');dest.mkdir(parents=True,exist_ok=True,mode=0o700)
path=dest/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
path.write_text(json.dumps(snapshot,indent=2));path.chmod(0o600)
def safe(value):
    if isinstance(value,dict):return {k:('[hidden]' if any(x in k.lower() for x in ('key','password','secret')) else safe(v)) for k,v in value.items()}
    if isinstance(value,list):return [safe(v) for v in value]
    return value
print('Wireless config:',json.dumps(safe(snapshot['wireless']),indent=2))
print('Wireless status:',json.dumps(safe(rpc(session,'network.wireless','status',{})),indent=2)[:14000])
print('Private backup:',path)
