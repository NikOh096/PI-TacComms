import datetime, json, os, time, urllib.request
from pathlib import Path

def rpc(host, sid, obj, method, args, timeout=6):
    data={'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}
    req=urllib.request.Request('http://'+host+'/ubus',data=json.dumps(data).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as response:value=json.load(response)
    result=value.get('result',[])
    if not result or result[0]!=0:raise RuntimeError(obj+'.'+method+' failed: '+str(result[:1]))
    return result[1] if len(result)>1 else {}

def login(host, password):
    return rpc(host,'0'*32,'session','login',{'username':'root','password':password})['ubus_rpc_session']

def set_admin_password(host, sid):
    rpc(host,sid,'luci','setPassword',{'username':'root','password':PASSWORD})
    fresh=login(host,PASSWORD)
    print('Administrator password changed; fresh login verified.',flush=True)
    return fresh

def save_backup(name, before):
    folder=Path('/var/lib/taccomms/router-backups')
    folder.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=folder/(name+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
    path.write_text(json.dumps(before,indent=2));path.chmod(0o600)
    return path
