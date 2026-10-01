"""Configure one explicitly identified HD01; confirm only through the gateway side."""
import datetime, importlib.util, json, subprocess, sys
from pathlib import Path
base=Path(__file__).resolve().parent
settings=json.loads((base/'private/tc-network.json').read_text())
password=settings['password']
old_name=sys.argv[1]
new_name=settings['nodes'][old_name]
suffix={'HT-HD01-BFD0':'2a:bf:d0','HT-HD01-A04E':'2a:a0:4e'}[old_name]
# Refuse to alter a dongle without a working Pi-side verification path.
preflight=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(base/'tc-pairing-preflight.py'),'--python'],capture_output=True,text=True)
if preflight.returncode:raise RuntimeError('Pi management unavailable; no HD01 changes made.')
spec=importlib.util.spec_from_file_location('browser',base/'phone-browser.py')
browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
sid=browser.rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
board=browser.rpc(sid,'system','board',{})
assert board.get('model')=='Heltec HT-HD01-V2' and board.get('hostname')==old_name, 'Unexpected device identity'
before={n:browser.rpc(sid,'uci','get',{'config':n})['values'] for n in ('system','wireless','network','dhcp','firewall')}
backup=base/'private'/('before-'+new_name+'-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
backup.write_text(json.dumps(before,indent=2))
system=next(k for k,v in before['system'].items() if v.get('.type')=='system')
browser.rpc(sid,'uci','set',{'config':'system','section':system,'values':{'hostname':new_name}})
browser.rpc(sid,'uci','set',{'config':'wireless','section':'radio1','values':{'country':'US','channel':'25','disabled':'0'}})
browser.rpc(sid,'uci','set',{'config':'wireless','section':'default_radio1','values':{'mode':'sta','network':'lan','ssid':'TC-HTRT01','encryption':'sae','key':password,'wds':'1','disabled':'0','dpp':'0'}})
browser.rpc(sid,'uci','set',{'config':'wireless','section':'default_radio0','values':{'mode':'ap','network':'lan','ssid':new_name,'encryption':'psk2','key':password,'disabled':'0'}})
bridge=next((k for k,v in before['network'].items() if v.get('.type')=='device' and v.get('name')=='br-lan'),None)
if bridge:
    assert before['network'][bridge].get('type')=='bridge'
else:
    browser.rpc(sid,'uci','add',{'config':'network','type':'device','name':'taccomms_lan','values':{'name':'br-lan','type':'bridge','ports':['eth0.1']}})
browser.rpc(sid,'uci','set',{'config':'network','section':'lan','values':{'proto':'dhcp','device':'br-lan'}})
for option in ('ipaddr','netmask','ip6assign'):
    if option in before['network']['lan']:browser.rpc(sid,'uci','delete',{'config':'network','section':'lan','option':option})
browser.rpc(sid,'uci','set',{'config':'dhcp','section':'lan','values':{'ignore':'1','ra':'disabled','dhcpv6':'disabled'}})
if 'ahwlan' in before['network']:browser.rpc(sid,'uci','delete',{'config':'network','section':'ahwlan'})
if 'ahwlan' in before['dhcp']:browser.rpc(sid,'uci','delete',{'config':'dhcp','section':'ahwlan'})
prefix='PASSWORD='+repr(password)+'\nSESSION='+repr(sid)+'\nOLD_NAME='+repr(old_name)+'\nNEW_NAME='+repr(new_name)+'\nMAC_SUFFIX='+repr(suffix)+'\n'
script=base/'private/tc-hd01-confirm-current.py'
script.write_text(prefix+(base/'tc-router-common.py').read_text()+'\n'+(base/'confirm-tc-hd01.py').read_text())
try:
    try:browser.rpc(sid,'uci','apply',{'timeout':120,'rollback':True})
    except Exception as exc:print('Apply response interrupted:',type(exc).__name__,flush=True)
    print('Applying',new_name,'with automatic rollback pending bridge verification.',flush=True)
    result=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(script),'--python','--timeout','110'],capture_output=True,text=True)
    print(result.stdout,flush=True)
    if result.returncode:
        print(result.stderr,flush=True)
        raise SystemExit(result.returncode)
    record=next(json.loads(line.removeprefix('PAIRING_RESULT=')) for line in result.stdout.splitlines() if line.startswith('PAIRING_RESULT='))
    (base/(new_name.lower()+'-verified.json')).write_text(json.dumps(record,indent=2))
finally:script.unlink(missing_ok=True)
