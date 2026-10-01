import json, subprocess, urllib.request
def rpc(sid,obj,method,args):
    req=urllib.request.Request('http://10.42.0.1/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=6) as r:v=json.load(r)
    result=v.get('result',[])
    if not result or result[0]!=0:raise RuntimeError(obj+'.'+method+' failed')
    return result[1] if len(result)>1 else {}
sid=rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
print('Gateway:',rpc(sid,'system','board',{}))
for name in ('network','wireless','system'):
    values=rpc(sid,'uci','get',{'config':name})['values']
    safe={k:{a:b for a,b in v.items() if a in ('.type','type','device','mode','network','ssid','country','channel','disabled','wds','proto','ipaddr','hostname','ports')} for k,v in values.items()}
    print(name,json.dumps(safe))
print('Leases:',rpc(sid,'luci-rpc','getDHCPLeases',{}))
print('Pi power:',subprocess.check_output(['vcgencmd','get_throttled'],text=True).strip())
print('Pi uptime:',subprocess.check_output(['uptime','-p'],text=True).strip())
for path in ('/luci-static/resources/view/system/admin/password.js','/luci-static/resources/view/system/admin.js'):
    try:
        with urllib.request.urlopen('http://10.42.0.1'+path,timeout=5) as r:s=r.read().decode()
        start=s.find('setPassword')
        if start>=0:print('Password API source:',path,s[max(0,start-130):start+260]);break
    except OSError:pass
