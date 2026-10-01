import datetime, grp, hashlib, json, os, pwd, re, secrets, shutil, sqlite3, subprocess
from pathlib import Path

def run(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)

stage=Path('/home/niko/taccomms-stage')
manifest=json.loads((stage/'manifest.json').read_text())
for name,digest in manifest.items():
    assert hashlib.sha256((stage/name).read_bytes()).hexdigest()==digest, name
backup=Path('/var/lib/halow-setup/backups')/('before-secure-admin-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(mode=0o700,parents=True)
config=Path('/etc/mumble/mumble-server.ini')
shutil.copy2(config,backup/'mumble-server.ini')
shutil.copy2('/etc/systemd/system/halow-console.service',backup/'halow-console.service')
shutil.copy2('/usr/local/bin/halow-console',backup/'console.py')
(backup/'enabled-units.txt').write_text(run('systemctl','list-unit-files','--state=enabled','--no-pager'))
(backup/'nftables.txt').write_text(run('nft','list','ruleset'))
with sqlite3.connect('file:/var/lib/mumble-server/mumble-server.sqlite?mode=ro',uri=True) as src,sqlite3.connect(backup/'mumble.sqlite') as dst:
    src.backup(dst)
for p in backup.iterdir(): p.chmod(0o600)
try: pwd.getpwnam('taccomms')
except KeyError: subprocess.run(['useradd','--system','--user-group','--home-dir','/var/lib/taccomms-ui','--shell','/usr/sbin/nologin','taccomms'],check=True)
subprocess.run(['usermod','-a','-G','video,input,i2c,gpio,tty','taccomms'],check=True)
subprocess.run(['usermod','-a','-G','taccomms','niko'],check=True)
opt=Path('/opt/taccomms'); opt.mkdir(mode=0o755,exist_ok=True)
for name in manifest:
    if name.endswith('.py'):
        shutil.copyfile(stage/name,opt/name); (opt/name).chmod(0o644)
shutil.copyfile('/usr/local/bin/halow-console',opt/'legacy.py')
for name in ('taccomms-admin.service','taccomms-screen.service'):
    shutil.copyfile(stage/name,Path('/etc/systemd/system')/name)
private=Path('/etc/taccomms'); private.mkdir(mode=0o700,exist_ok=True)
key=private/'ice.json'
if key.exists(): secret=json.loads(key.read_text())['secret']
else:
    secret=secrets.token_urlsafe(48)
    key.write_text(json.dumps({'secret':secret})); key.chmod(0o600)
contents=config.read_text()
for name,value in {'ice':'tcp -h 127.0.0.1 -p 6502','icesecretread':secret,'icesecretwrite':secret,'registerName':'TacComms'}.items():
    pattern=r'(?m)^'+re.escape(name)+r'=.*$'
    contents=re.sub(pattern,lambda m:name+'='+value,contents) if re.search(pattern,contents) else contents+'\n'+name+'='+value+'\n'
config.write_text(contents)
config.chmod(0o640); os.chown(config,0,grp.getgrnam('mumble-server').gr_gid)
wrapper=Path('/usr/local/bin/taccomms-admin')
wrapper.write_text('#!/bin/sh\nexec /usr/bin/python3 /opt/taccomms/cli.py\n'); wrapper.chmod(0o755)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','mumble-server.service'],check=True)
subprocess.run(['systemctl','enable','--now','taccomms-admin.service'],check=True)
print('Backup:',backup)
print(run('systemctl','is-active','mumble-server.service','taccomms-admin.service'))
print(run('ss','-lnt','sport','=','6502'))
print('PIN enrollment remains unset; no PINs were supplied or stored.')
