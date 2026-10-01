import json,urllib.request
base='http://10.42.0.1/ubus'
def request(method,params):
    req=urllib.request.Request(base,data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=6) as r:return json.load(r)
sid=request('call',['0'*32,'session','login',{'username':'root','password':'heltec.org'}])['result'][1]['ubus_rpc_session']
for obj in ('luci','luci-rpc'):
    data=request('list',[sid,obj])
    print(obj, json.dumps(data))
