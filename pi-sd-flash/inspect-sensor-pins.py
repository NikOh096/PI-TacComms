from pathlib import Path
import subprocess

for command in (['pinctrl', 'get', '3,5,6'], ['dtoverlay', '-l'], ['systemctl', 'is-active', 'mumble-server.service']):
    print(' '.join(command), flush=True)
    subprocess.run(command, check=False)
print('GPIO consumers:')
path = Path('/sys/kernel/debug/gpio')
if path.exists(): print(path.read_text())
print('Boot GPIO overlays:')
for line in Path('/boot/firmware/config.txt').read_text().splitlines():
    if line.startswith(('dtoverlay=', 'dtparam=')): print(line)
print('Existing I2C buses:', ', '.join(str(p) for p in Path('/dev').glob('i2c-*')))
