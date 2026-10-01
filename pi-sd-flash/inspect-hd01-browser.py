import importlib.util,json,datetime
from pathlib import Path
base=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('browser',base/'phone-browser.py');browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
sid=browser.rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
board=browser.rpc(sid,'system','board',{})
print('HD01:',json.dumps({k:board.get(k) for k in ('model','board_name','hostname','release')}))
assert 'HD01' in board.get('hostname','').upper() or 'HD01' in board.get('model','').upper()
snapshot={name:browser.rpc(sid,'uci','get',{'config':name})['values'] for name in ('wireless','network','dhcp','firewall')}
dest=base/'private'/('hd01-before-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
dest.write_text(json.dumps(snapshot,indent=2))
def safe(value):
    if isinstance(value,dict):return {k:'[hidden]' if any(t in k.lower() for t in ('key','secret','password')) else safe(v) for k,v in value.items()}
    if isinstance(value,list):return [safe(v) for v in value]
    return value
for name in ('wireless','network','dhcp'):print(name,json.dumps(safe(snapshot[name]),indent=2))
print('Private backup saved.')
