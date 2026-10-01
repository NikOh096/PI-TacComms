"""Rotate the generated Pi login password and keep its private credential file current."""
import json
from pathlib import Path
import secrets
import subprocess
import sys

base = Path(__file__).resolve().parent
sys.path.insert(0,str(base/'setup-tools'))
from passlib.hash import sha512_crypt
credentials = json.loads((base/'private/credentials.json').read_text())
old = credentials['pi_password']
password = '-'.join(secrets.choice(['cedar','river','maple','stone','cloud','lake','silver','otter','moss','harbor','pine','fern']) for _ in range(4)) + '-' + str(secrets.randbelow(9000)+1000)
digest = sha512_crypt.using(rounds=200000).hash(password)
remote = base/'private/rotate-login-remote.py'
remote.write_text('import subprocess\nsubprocess.run(["chpasswd", "-e"], input='+repr('niko:'+digest+'\n')+', text=True, check=True)\nprint("Pi login password updated.")\n')
result = subprocess.run([sys.executable,str(base/'pi-admin.py'),str(remote),'--python'])
if result.returncode:
    raise SystemExit(result.returncode)
credentials.update(pi_password=password,password_hash=digest)
(base/'private/credentials.json').write_text(json.dumps(credentials,indent=2)+'\n')
human = base/'private/HaLow-Pi-credentials.txt'
human.write_text(human.read_text().replace(old,password))
settings_path = base/'halow-setup/settings.json'
settings = json.loads(settings_path.read_text())
settings['password_hash'] = digest
settings_path.write_text(json.dumps(settings,indent=2)+'\n')
print('Private credentials file updated. Passwords were not printed.')
