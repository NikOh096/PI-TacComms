import json,os,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from client import request
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT).strip()
print('Security:',json.dumps(request('state')))
print('Calibration saved:',Path('/var/lib/taccomms-ui/touch.json').exists())
print(run('systemctl','show','taccomms-screen.service','taccomms-admin.service','mumble-server.service','-p','Id','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'))
print(run('ps','-C','python3,mumble-server','-o','user,pid,pcpu,rss,args'))
print(run('journalctl','-u','taccomms-screen.service','-n','15','--no-pager','-o','cat'))
print(run('ddcutil','--bus','20','--skip-ddc-checks','--mccs','2.2','--disable-dynamic-sleep','--sleep-multiplier','2','getvcp','D6'))
denied=subprocess.run(['runuser','-u','nobody','--','python3','-c',"import socket;s=socket.socket(socket.AF_UNIX);s.connect('/run/taccomms/admin.sock')"],capture_output=True,text=True)
assert denied.returncode!=0 and 'PermissionError' in denied.stderr
print('PASS: unrelated local account cannot open the admin socket.')
