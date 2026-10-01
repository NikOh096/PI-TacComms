import subprocess
from pathlib import Path
for args in [('systemctl','cat','mumble-server.service'),('systemctl','get-default'),('dpkg','-L','mumble-server')]:
    print(subprocess.check_output(args,text=True))
for p in Path('/etc').glob('mumble*/*'):
    if p.is_file():
        print('Config file:',str(p))
        if p.suffix in ('.ini','.conf'):
            for line in p.read_text().splitlines():
                if line.split('=',1)[0].strip() in ('database','ice','port','host','users','bandwidth','registerName'):
                    print(line)
print('UI-related groups:')
print(subprocess.check_output(['getent','group','video','input','i2c','gpio','tty'],text=True))
