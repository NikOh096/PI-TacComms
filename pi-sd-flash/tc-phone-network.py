import importlib.util,json,shlex,sys
from pathlib import Path
base=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('phone',base/'android-phone.py')
phone=importlib.util.module_from_spec(spec);spec.loader.exec_module(phone)
ssid=sys.argv[1]
assert ssid in ('TC-HTRT01','TC-HTHD01','TC-HTHD02','HT-HD01-BFD0','HT-HD01-A04E')
password=json.loads((base/'private/tc-network.json').read_text())['password'] if ssid.startswith('TC-') else 'heltec.org'
phone.adb('shell','cmd','wifi','connect-network',shlex.quote(ssid),'wpa2',shlex.quote(password))
print('Requested phone Wi-Fi connection:',ssid)
