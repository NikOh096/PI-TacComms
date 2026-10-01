import fcntl
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess

def run(*args):
    r = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=15)
    print(' '.join(args), '\n' + r.stdout[:14000])

for name in ('PIL', 'Ice', 'google.protobuf', 'cryptography'):
    try:
        print('Python module:', name, bool(importlib.util.find_spec(name)))
    except ModuleNotFoundError:
        print('Python module:', name, False)
run('dpkg-query', '-W', '-f=${binary:Package} ${Version}\n', 'python3-pil', 'python3-zeroc-ice', 'libzeroc-ice3.7t64', 'libmcpp0', 'nftables')
run('ss', '-lntup')
run('sshd', '-T')
run('systemctl', 'list-unit-files', '--state=enabled', '--no-pager')
run('sh', '-c', 'command -v nft >/dev/null && nft list ruleset')
run('dpkg', '-L', 'mumble-server')
for path in Path('/sys/class/input').glob('event*/device/name'):
    if 'ADS7846' in path.read_text():
        device = '/dev/input/' + path.parents[1].name
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        try:
            for axis in (0, 1, 24):
                buffer = bytearray(24)
                fcntl.ioctl(fd, 0x80184540 + axis, buffer, True)
                print('Touch axis', axis, struct.unpack('iiiiii', buffer))
        finally:
            os.close(fd)
for name in ('virtual_size', 'bits_per_pixel', 'stride'):
    path = Path('/sys/class/graphics/fb0') / name
    if path.exists():
        print('Framebuffer', name, path.read_text().strip())
print('Monospace fonts:', [str(p) for p in Path('/usr/share/fonts/truetype').glob('*/DejaVuSansMono*.ttf')])
for path in Path('/usr/share').glob('mumble*/*.ice'):
    print('Installed Ice interface:', path)
    text = path.read_text()
    for marker in ('struct User', 'struct Ban', 'enum UserInfo'):
        start = text.find(marker)
        print(text[start:start+5500] if start >= 0 else marker + ': not found')
