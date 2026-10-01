#!/usr/bin/python3
"""Show live state without exposing passwords; save a boot report when run by systemd."""
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def capture(*args):
    result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, timeout=10)
    return result.stdout.strip()


def report():
    raw = capture('ip', '-j', '-4', 'address', 'show', 'dev', 'eth0')
    interfaces = json.loads(raw or '[]')
    addresses = [a['local'] for i in interfaces for a in i.get('addr_info', [])
                 if a.get('scope') == 'global']
    active = capture('systemctl', 'is-active', 'mumble-server.service')
    tcp = bool(capture('ss', '-H', '-lnt', 'sport = :64738'))
    udp = bool(capture('ss', '-H', '-lnu', 'sport = :64738'))
    devices = Path('/proc/bus/input/devices').read_text()
    touch = bool(re.search(r'ADS7846|XPT2046', devices, re.I))
    data = {'hostname': 'halow-pi', 'ethernet_ipv4': addresses, 'mumble': active,
            'tcp_64738': tcp, 'udp_64738': udp, 'touch_controller_detected': touch,
            'touch_alignment_and_phone_audio_verified': False,
            'time': time.strftime('%Y-%m-%d %H:%M:%S')}
    lines = ['HaLow Voice - Raspberry Pi', '',
             'Phone server address: ' + (', '.join(addresses) or 'Waiting for Ethernet DHCP from the router'),
             'Port: 64738 (TCP and UDP)', 'Mumble service: ' + active,
             'TCP listening: ' + str(tcp), 'UDP listening: ' + str(udp),
             'Touch controller detected: ' + str(touch), '',
             'Use the shared Mumble password from the credentials file on your PC.',
             'Use push-to-talk and 24 kbit/s Opus on phones.',
             'Touch alignment and a call between two phones still need a hands-on test.',
             '', 'Updated: ' + data['time']]
    return data, '\n'.join(lines) + '\n'


if __name__ == '__main__':
    data, text = report()
    if '--save' in sys.argv:
        for attempt in range(15):
            if data['ethernet_ipv4']:
                break
            time.sleep(2)
            data, text = report()
        target = Path('/boot/firmware/halow-setup')
        (target / 'status.json').write_text(json.dumps(data, indent=2) + '\n')
        (target / 'status.txt').write_text(text)
    print(text)
    if '--wait' in sys.argv:
        input('Press Enter to close...')
