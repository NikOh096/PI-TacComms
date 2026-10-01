"""Read-only gateway checks over the phone's existing local browser tab."""
import importlib.util
from pathlib import Path

base = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('browser', base / 'phone-browser.py')
browser = importlib.util.module_from_spec(spec)
spec.loader.exec_module(browser)
sid = browser.rpc('0' * 32, 'session', 'login',
                  {'username': 'root', 'password': 'heltec.org'})['ubus_rpc_session']
board = browser.rpc(sid, 'system', 'board', {})
assert board.get('hostname') == 'WHL-AP-72AA', 'Wrong gateway; stopping.'
print('Gateway:', board.get('model'), board.get('hostname'))
leases = browser.rpc(sid, 'luci-rpc', 'getDHCPLeases', {}).get('dhcp_leases', [])
pi = [v for v in leases if v.get('macaddr', '').lower() == 'dc:a6:32:b9:ef:13'
      or v.get('hostname', '').lower() == 'halow-pi']
print('Pi DHCP lease (may be retained while offline):', pi)
reservation = browser.rpc(sid, 'uci', 'get', {'config': 'dhcp', 'section': 'taccomms_pi'})
print('Pi reservation:', reservation)
