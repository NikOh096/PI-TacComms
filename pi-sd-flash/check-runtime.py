import json
from pathlib import Path
import subprocess
import urllib.request

for command in [
    ['systemctl','is-enabled','mumble-server.service','halow-console.service'],
    ['systemctl','is-active','mumble-server.service','halow-console.service'],
    ['vcgencmd','get_throttled'],['pinctrl','get','3'],['ip','-4','route'],
    ['journalctl','-b','-u','halow-console.service','--no-pager','-n','8']]:
    result = subprocess.run(command,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    print(' '.join(command), '\n',result.stdout)
try:
    with urllib.request.urlopen('http://10.42.0.1/',timeout=5) as response:
        print('Router HTTP:',response.status,'Final URL:',response.url)
        print(response.read(800).decode(errors='replace'))
except Exception as error:
    print('Router HTTP:',type(error).__name__)
screen=Path('/dev/vcs1').read_bytes().decode('ascii',errors='replace')
print('Visible console buffer:')
for start in range(0,len(screen),40):
    print(screen[start:start+40].rstrip())
