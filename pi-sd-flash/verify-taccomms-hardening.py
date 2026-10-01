import subprocess,sys,json,os
from pathlib import Path
def run(*args):return subprocess.check_output(args,text=True).strip()
sys.path.insert(0,'/opt/taccomms')
from client import request
assert run('systemctl','is-active','mumble-server.service')=='active'
assert run('systemctl','is-active','taccomms-screen.service')=='active'
assert run('systemctl','is-active','taccomms-admin.service')=='active'
rules=run('nft','list','ruleset')
assert 'nm-shared-usb0' in rules and 'table inet taccomms' in rules
assert 'policy drop' in rules
settings=run('sshd','-T')
for item in ('passwordauthentication no','permitrootlogin no','allowusers niko','allowtcpforwarding no','x11forwarding no'):
    assert item in settings,item
print('PASS: fresh USB SSH connection, firewall, preserved USB sharing, SSH key-only restrictions.')
print('PIN security state:',json.dumps(request('state')))
print('Listening TCP ports:')
print(run('ss','-lnt'))
print('New UI log:')
print(run('journalctl','-u','taccomms-screen.service','-n','12','--no-pager','-o','cat'))
run('systemctl','stop','taccomms-firewall-rollback.timer')
print('Firewall rollback cancelled after fresh-session verification.')
