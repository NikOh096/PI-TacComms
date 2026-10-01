"""Read-only gateway inventory; omit passwords and session tokens from output."""
import json
import urllib.request

base = 'http://10.42.0.1'
def rpc(session, object_name, method, arguments):
    payload = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'call',
                          'params': [session, object_name, method, arguments]}).encode()
    request = urllib.request.Request(base + '/ubus', data=payload,
                                     headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)

try:
    login = rpc('0' * 32, 'session', 'login', {'username': 'root', 'password': 'heltec.org'})
    result = login.get('result', [])
    if not result or result[0] != 0:
        print('Gateway default login not accepted:', result[0] if result else login.get('error', {}).get('code'))
        raise SystemExit(0)
    session = result[1]['ubus_rpc_session']
    print('Gateway login accepted; reading network state only.')
    board = rpc(session, 'system', 'board', {}).get('result', [])
    if len(board) > 1:
        print('Gateway:', json.dumps({k: board[1].get(k) for k in ('model', 'board_name', 'hostname', 'release')}))
    fields = {
        'wireless': ('.type', 'type', 'device', 'mode', 'network', 'ssid', 'country', 'channel', 'bandwidth', 'disabled'),
        'network': ('.type', 'type', 'proto', 'device', 'ifname', 'ports', 'ipaddr', 'netmask', 'gateway'),
        'dhcp': ('.type', 'interface', 'start', 'limit', 'leasetime', 'ignore', 'ip', 'mac', 'name'),
    }
    for config, allowed in fields.items():
        response = rpc(session, 'uci', 'get', {'config': config}).get('result', [])
        if len(response) > 1:
            sections = response[1].get('values', {})
            filtered = {name: {k: section[k] for k in allowed if k in section} for name, section in sections.items()}
            print(config + ':', json.dumps(filtered))
        else:
            print(config + ': unavailable')
except (OSError, ValueError, KeyError) as error:
    print('Gateway inventory unavailable:', type(error).__name__)
