import importlib.util,json
from pathlib import Path
base=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('browser',base/'phone-browser.py');browser=importlib.util.module_from_spec(spec);spec.loader.exec_module(browser)
sid=browser.rpc('0'*32,'session','login',{'username':'root','password':'heltec.org'})['ubus_rpc_session']
board=browser.rpc(sid,'system','board',{})
print('Device at phone gateway:',board.get('model'),board.get('hostname'))
wireless=browser.rpc(sid,'uci','get',{'config':'wireless'})['values']
network=browser.rpc(sid,'uci','get',{'config':'network'})['values']
print('HaLow interface:',{k:wireless.get('default_radio1',{}).get(k) for k in ('mode','network','ssid','wds')})
print('LAN:',{k:network.get('lan',{}).get(k) for k in ('proto','ipaddr')})
result={'model':board.get('model'),'hostname':board.get('hostname'),'ssid':wireless.get('default_radio1',{}).get('ssid'),'network':wireless.get('default_radio1',{}).get('network'),'lan_proto':network.get('lan',{}).get('proto')}
(base/'hd01-last-verified.json').write_text(json.dumps(result,indent=2))
