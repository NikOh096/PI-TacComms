import json,urllib.request
base='http://10.42.0.1'
def post(method,params):
    req=urllib.request.Request(base+'/ubus',data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=10) as r:return json.load(r)
sid=post('call',['0'*32,'session','login',{'username':'root','password':'heltec.org'}])['result'][1]['ubus_rpc_session']
for obj,method,args in [('network.wireless','status',{}),('file','exec',{'command':'/sbin/uci','params':['get','wireless.radio1.country']}),('iwinfo','devices',{})]:
    value=post('call',[sid,obj,method,args]); print(obj,method,json.dumps(value))
for path in ('/luci-static/resources/view/morse/wizard.js','/luci-static/resources/morse/uci.js','/luci-static/resources/tools/morse/wizard.js'):
    try:
        with urllib.request.urlopen(base+path,timeout=10) as r: data=r.read().decode()
        print('Wizard resource:',path,'length:',len(data))
        for keyword in ('country','channel','bw','op_class','disabled'):
            index=data.find("'"+keyword+"'")
            if index>=0:print(keyword,data[max(0,index-80):index+180])
    except Exception as exc:print(path,type(exc).__name__)
