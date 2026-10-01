import json, re, subprocess, sys
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble
path=Path('/etc/mumble/mumble-server.ini')
text=path.read_text()
match=re.search(r'(?m)^serverpassword=(.*)$',text)
marker=Path('/etc/taccomms/password-migrated')
if not marker.exists():
    if not match or not match.group(1):
        raise RuntimeError('Expected existing default password before migration')
    m=Mumble()
    try:
        server=m.server()
        server.setConf('password',match.group(1).strip())
        # Ice clearing an override falls back to the INI default. Moving the
        # current secret into server 1's database makes password-clear effective.
        updated=text[:match.start()]+ 'serverpassword=' +text[match.end():]
        temp=path.with_suffix('.new')
        temp.write_text(updated); temp.chmod(0o640)
        import os
        os.chown(temp,path.stat().st_uid,path.stat().st_gid)
        temp.replace(path)
        subprocess.run(['systemctl','restart','mumble-server.service'],check=True)
        marker.write_text('Server 1 password preserved in the Mumble database.\n'); marker.chmod(0o600)
        print('Existing password preserved; default fallback removed for proper password-clear behavior.')
    finally: m.ice.destroy()
else: print('Password migration already completed.')
