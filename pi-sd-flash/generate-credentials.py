import json
import pathlib
import secrets
import subprocess
import sys
BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'setup-tools'))
from passlib.hash import sha512_crypt
private = BASE / 'private'
private.mkdir(exist_ok=True)
record_path = private / 'credentials.json'
if record_path.exists():
    record = json.loads(record_path.read_text())
else:
    words = ['cedar','maple','copper','falcon','river','meadow','summit','harbor','willow','forest','silver','cobalt','comet','orchid','quartz','raven','maple','spruce','birch','acorn','sunset','valley','timber','coral','otter','eagle','pine','cloud','amber','brook','island','clover']
    def phrase(): return '-'.join(secrets.choice(words) for _ in range(4)) + '-' + str(secrets.randbelow(9000)+1000)
    record = {'username': 'niko', 'hostname': 'halow-pi', 'pi_password': phrase(), 'mumble_password': phrase(), 'admin_password': secrets.token_urlsafe(24)}
    record['password_hash'] = sha512_crypt.using(rounds=200000).hash(record['pi_password'])
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
key = private / 'halow-pi-ed25519'
if not key.exists():
    subprocess.run(['C:/Windows/System32/OpenSSH/ssh-keygen.exe','-t','ed25519','-N','','-f',str(key),'-C','Niko PC - HaLow Pi management'],check=True,stdout=subprocess.DEVNULL)
bundle = BASE / 'halow-setup'
public = key.with_suffix('.pub').read_text().strip()
settings = {k: record[k] for k in ('username','hostname','password_hash','mumble_password','admin_password')}
settings['ssh_public_key'] = public
(bundle / 'settings.json').write_text(json.dumps(settings, indent=2), encoding='utf-8')
instructions = f'''HaLow Pi credentials

Pi hostname: {record['hostname']}.local
Pi username: {record['username']}
Pi desktop password: {record['pi_password']}
SSH: key-based access from this PC using {key}

Mumble server name: HaLow Voice
Mumble server address: use the Pi Ethernet IP shown in the desktop HaLow Status tool
Mumble port: 64738 (TCP and UDP)
Mumble participant password: {record['mumble_password']}
Participant username: each phone should use its own name

Mumble administrator username: SuperUser
Mumble administrator password: {record['admin_password']}
Keep the administrator password separate from the participant password.

USB-C management address: 10.12.194.1 (when Windows internet sharing is off)
The HaLow Ethernet IP may be different; phones must use the Ethernet IP.

The setup has only been staged until the Pi boots and completes it.
'''
(private / 'HaLow-Pi-credentials.txt').write_text(instructions, encoding='utf-8')
print('Generated local credentials and SSH key. Passwords are saved in the private credentials file, not printed.')
