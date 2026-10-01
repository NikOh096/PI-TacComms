import hashlib
import json
from pathlib import Path
import subprocess

before = json.loads(Path('/var/lib/halow-setup/taccomms-deployment-before.json').read_text())
pid = subprocess.check_output(['systemctl', 'show', 'mumble-server.service', '-p', 'MainPID', '--value'], text=True).strip()
assert pid == before['mumble_pid'], 'Mumble process changed during dashboard deployment'
subprocess.run(['systemctl', 'is-active', 'mumble-server.service', 'halow-console.service'], check=True)
for name in ('/boot/firmware/config.txt', '/etc/systemd/system/halow-console.service'):
    assert hashlib.sha256(Path(name).read_bytes()).hexdigest() == before['sha256'][name]
sources = [Path('/usr/local/bin/halow-console'), Path('/var/lib/halow-setup/console.py'), Path('/boot/firmware/halow-setup/console.py')]
assert len({hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}) == 1
for path in sources:
    compile(path.read_text(), str(path), 'exec')
rows, columns = Path('/dev/vcsa1').read_bytes()[:2]
screen = Path('/dev/vcs1').read_bytes().decode('ascii', errors='replace')
assert screen[:columns].startswith('TacComms'), 'Updated heading is not visible on tty1'
print('Live console (' + str(columns) + ' x ' + str(rows) + '):')
for start in range(0, len(screen), columns):
    print(screen[start:start+columns].rstrip())
print('Mumble PID unchanged:', pid)
print('Boot display configuration and systemd service unchanged.')
print('PASS: live TacComms layout, source integrity, and service continuity.')
