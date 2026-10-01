import hashlib, json, subprocess
from pathlib import Path
base = Path('/home/niko/taccomms-stage')
records = json.loads((base/'packages.json').read_text())
files = []
for item in records:
    p = base/item['filename']
    assert hashlib.sha256(p.read_bytes()).hexdigest() == item['sha256']
    files.append(str(p))
subprocess.run(['apt-get', '--simulate', 'install', *files], check=True)
subprocess.run(['dpkg', '-i', *files], check=True)
import Ice
print('Ice version:', Ice.stringVersion())
subprocess.run(['systemctl', 'cat', 'halow-console.service'], check=True)
import fcntl, os, struct
fd = os.open('/dev/fb0', os.O_RDONLY)
b = bytearray(160)
fcntl.ioctl(fd, 0x4600, b, True)
print('Framebuffer var first 20 ints:', struct.unpack_from('20I', b))
os.close(fd)
print('Mumble config nonsecret fields:')
for line in Path('/etc/mumble/mumble-server.ini').read_text().splitlines():
    if line.split('=', 1)[0].strip() in ('database', 'ice', 'port', 'host', 'users', 'bandwidth', 'registerName'):
        print(line)
