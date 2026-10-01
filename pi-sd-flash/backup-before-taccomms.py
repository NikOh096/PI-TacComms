import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

assert subprocess.check_output(['hostname'], text=True).strip() == 'halow-pi'
subprocess.run(['systemctl', 'is-active', '--quiet', 'mumble-server.service'], check=True)
pid = subprocess.check_output(['systemctl', 'show', 'mumble-server.service', '-p', 'MainPID', '--value'], text=True).strip()
assert int(pid) > 0
directory = Path('/var/lib/halow-setup/backups') / time.strftime('before-taccomms-%Y%m%d-%H%M%S')
directory.mkdir(parents=True, mode=0o700)
files = {}
for source, name in [('/usr/local/bin/halow-console', 'console-live.py'),
                     ('/var/lib/halow-setup/console.py', 'console-installed.py'),
                     ('/boot/firmware/halow-setup/console.py', 'console-boot.py'),
                     ('/boot/firmware/config.txt', 'config.txt'),
                     ('/etc/systemd/system/halow-console.service', 'halow-console.service')]:
    path = Path(source)
    if path.exists():
        shutil.copy2(path, directory/name)
        files[source] = hashlib.sha256(path.read_bytes()).hexdigest()
record = {'backup_directory': str(directory), 'mumble_pid': pid, 'sha256': files}
text = json.dumps(record, indent=2) + '\n'
(directory/'manifest.json').write_text(text)
Path('/var/lib/halow-setup/taccomms-deployment-before.json').write_text(text)
os.sync()
print('Verified backup:', directory)
print('Mumble process before dashboard update:', pid)
