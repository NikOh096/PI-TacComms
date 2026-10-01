import csv,io,json,urllib.request
base='http://10.42.0.1'
with urllib.request.urlopen(base+'/halow-channels.csv',timeout=10) as r: data=r.read().decode()
rows=[r for r in csv.DictReader(io.StringIO(data)) if r['country_code']=='US']
print('US center channels:',json.dumps([r for r in rows if r['s1g_chan'] in ('23','24','25','26','27')],indent=2))
def rpc(sid,obj,method,args):
    req=urllib.request.Request(base+'/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
sid=rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['result'][1]['ubus_rpc_session']
for method in ('set','add','apply','confirm'):
    print('Access',method,json.dumps(rpc(sid,'session','access',{'scope':'ubus','object':'uci','function':method})))
def safe(v):
    if isinstance(v,dict):return {k:'[hidden]' if any(s in k.lower() for s in ('key','secret','password')) else safe(value) for k,value in v.items()}
    if isinstance(v,list):return [safe(x) for x in v]
    return v
print('Runtime:',json.dumps(safe(rpc(sid,'luci-rpc','getWirelessDevices',{})))[:12000])
