import base64,importlib.util,json,subprocess,sys,datetime
from pathlib import Path
base=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('browser',base/'phone-browser.py');browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
sid=browser.rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
board=browser.rpc(sid,'system','board',{})
assert board.get('model')=='Heltec HT-HD01-V2' and board.get('hostname')=='HT-HD01-BFD0'
before={n:browser.rpc(sid,'uci','get',{'config':n})['values'] for n in ('wireless','network','dhcp')}
backup=base/'private'/('hd01-before-bridge-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
backup.write_text(json.dumps(before,indent=2))
browser.rpc(sid,'uci','set',{'config':'wireless','section':'radio1','values':{'country':'US','channel':'25','disabled':'0'}})
browser.rpc(sid,'uci','set',{'config':'wireless','section':'default_radio1','values':{'mode':'sta','network':'lan','ssid':'WHL-AP-72AA','encryption':'sae','key':'heltec.org','wds':'1','disabled':'0'}})
browser.rpc(sid,'uci','set',{'config':'network','section':'lan','values':{'proto':'dhcp'}})
for option in ('ipaddr','netmask','ip6assign'):
    if option in before['network']['lan']:browser.rpc(sid,'uci','delete',{'config':'network','section':'lan','option':option})
browser.rpc(sid,'uci','set',{'config':'dhcp','section':'lan','values':{'ignore':'1','ra':'disabled','dhcpv6':'disabled'}})
if 'ahwlan' in before['network']:browser.rpc(sid,'uci','delete',{'config':'network','section':'ahwlan'})
payload=json.dumps({'session':sid}).encode()
remote='import base64,json\nSESSION=json.loads(base64.b64decode('+repr(base64.b64encode(payload).decode())+'))["session"]\n'+(base/'confirm-hd01-bridge.py').read_text()
script=base/'private/confirm-hd01-current.py';script.write_text(remote)
try:
    try:
        browser.rpc(sid,'uci','apply',{'timeout':120,'rollback':True})
        print('HD01 bridge configuration applied; automatic rollback armed.',flush=True)
    except Exception as exc:
        print('Apply response interrupted; checking the HaLow side before confirming.',type(exc).__name__,flush=True)
    result=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(script),'--python','--timeout','110'])
    raise SystemExit(result.returncode)
finally: script.unlink(missing_ok=True)
