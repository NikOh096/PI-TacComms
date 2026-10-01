"""Windows preflight: syntax, package integrity, boot edits, and display wake behavior."""
import ast
import hashlib
import io
import json
from pathlib import Path
import struct
import re
import sys
import types
import textwrap
from unittest.mock import Mock

BASE = Path(__file__).resolve().parent
BUNDLE = BASE / 'halow-setup'
for source in BUNDLE.glob('*.py'):
    compile(source.read_text(encoding='utf-8'), str(source), 'exec')
    if b'\r' in source.read_bytes():
        raise AssertionError('Linux scripts must use LF: ' + source.name)
assert b'\r' not in (BUNDLE / 'bootstrap.sh').read_bytes()
settings = json.loads((BUNDLE / 'settings.json').read_text())
assert settings['username'] == 'niko' and settings['hostname'] == 'halow-pi'
assert settings['password_hash'].startswith('$6$')
assert settings['ssh_public_key'].startswith('ssh-ed25519 ')
for item in json.loads((BUNDLE / 'packages.json').read_text()):
    data = (BUNDLE / 'debs' / item['filename']).read_bytes()
    assert len(data) == item['size']
    assert hashlib.sha256(data).hexdigest() == item['sha256']

# Test the critical touch behavior without a real Linux TTY or display.
tree = ast.parse((BUNDLE / 'console.py').read_text())
selected = [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))
            and getattr(node, 'name', '') in ('plain', 'display_command', 'Console')]
clock = types.SimpleNamespace(monotonic=lambda: 100)
calls = []
def fake_command(*args, **kwargs):
    calls.append(args)
    return 0, ''
namespace = {'time': clock, 'command': fake_command, 'sys': sys, 'TIMEOUT': 60,
             'subprocess': types.SimpleNamespace(run=Mock(), DEVNULL=-3),
             'os': types.SimpleNamespace(environ={})}
exec(compile(ast.Module(body=selected, type_ignores=[]), '<console-state-test>', 'exec'), namespace)
console = namespace['Console']()
console.set_blank(True)
assert not console.asleep and not calls  # No illuminated black-screen fallback.
console.bus = '11'
console.power_mode = 'LCD suspend / tap to wake'
console.set_blank(True)
assert console.asleep and calls[-1][-3:] == ('setvcp', 'D6', '3')
console.activity(150)
assert not console.asleep and console.page == 0 and console.last_touch == 150
assert calls[-1][-3:] == ('setvcp', 'D6', '1')
console.activity(151)
assert console.page == 1
console.activity(152)
assert console.page == 2
console.activity(153)
assert console.page == 0
namespace['command'] = lambda *args, **kwargs: (1, 'simulated display failure')
console.set_blank(True)
assert not console.asleep and 'unavailable' in console.power_mode
assert '\x1b' not in namespace['plain']('\x1b[2Junsafe\nlog')
assert struct.calcsize('qqHHi') == 24

# Check the small-screen layout, failed-server warning, and reduced status polling.
namespace.update(re=re, textwrap=textwrap)
uptime_function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'format_uptime')
exec(compile(ast.Module(body=[uptime_function], type_ignores=[]), '<uptime-test>', 'exec'), namespace)
files = {'/sys/class/net/eth0/carrier': '1',
         '/boot/firmware/halow-setup/setup-state.txt': 'PROVISION COMPLETE',
         '/sys/class/thermal/thermal_zone0/temp': '45000',
         '/proc/uptime': '90000 0', '/proc/loadavg': '0.13 0.1 0.1 1/10 100'}
namespace['read_text'] = lambda name, default='': files.get(name, default)
active = True
calls.clear()
def status_command(*args, **kwargs):
    calls.append(args)
    if args[0] == 'systemctl':
        return 0, 'ActiveState=active\nSubState=running\nMainPID=100' if active else 'ActiveState=failed\nSubState=failed\nMainPID=0'
    if args[0] == 'ip':
        return 0, '2: eth0 inet 10.42.0.137/24'
    if args[0] == 'vcgencmd':
        return 0, 'throttled=0x0'
    if args[0] == 'pinctrl':
        return 0, '3: ip pu | lo'
    if args[0] == 'ps':
        return 0, '200 300 ps\n300 0.2 python3\n100 0.0 mumble-server'
    return 0, 'event ' + '\x1b[2J' + 'long message ' * 50
namespace['command'] = status_command
console = namespace['Console']()
console.bus = '20'
console.power_mode = 'LCD suspend / tap to wake'
first = console.frame(40, 15)
assert len(first) == 14 and all(len(line) <= 39 for line in first)
assert first[0].startswith('TacComms') and 'Server    RUNNING' in first
assert 'Uptime    1d 1h 0m' in first
assert len(calls) == 4
clock.monotonic = lambda: 101
second = console.frame(40, 15)
assert len(calls) == 4 and second[-1].endswith('59s')
clock.monotonic = lambda: 105
assert 'Power in  connected' in console.frame(40, 15)
assert len(calls) == 8
active = False
clock.monotonic = lambda: 110
assert 'Server stopped - check Logs' in console.frame(40, 15)
for page in (1, 2):
    console.page = page
    frame = console.frame(40, 15)
    assert len(frame) == 14 and all(len(line) <= 39 and '\x1b' not in line for line in frame)
    if page == 2:
        assert frame[3].endswith('mumble-server') and not any(line.endswith(' ps') for line in frame)
# A one-second countdown update must not repaint the header or status values.
console.page = 0
output = io.StringIO()
namespace['sys'] = types.SimpleNamespace(stdout=output, stderr=sys.stderr)
namespace['os'].get_terminal_size = lambda fd: (40, 15)
console.render()
output.seek(0)
output.truncate(0)
clock.monotonic = lambda: 111
console.render()
assert 'Tap:' in output.getvalue() and 'TacComms' not in output.getvalue()

manifest = ''.join(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + path.relative_to(BUNDLE).as_posix() + '\n'
                   for path in sorted(BUNDLE.rglob('*'))
                   if path.is_file() and path.name != 'BUNDLE-SHA256SUMS' and '__pycache__' not in path.parts)
(BUNDLE / 'BUNDLE-SHA256SUMS').write_text(manifest, encoding='ascii', newline='\n')
print('Passed: syntax, package SHA256s, account settings, sleep/wake, small-screen layout, status caching, partial redraws, log sanitization.')
print('Bundle manifest written. Hardware wake, display quality and real calls still require the Pi.')
