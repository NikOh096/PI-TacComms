import io
import json
import pathlib
import struct
import sys

BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'setup-tools'))
from dissect.extfs import ExtFS
from debian.deb822 import Deb822

class CardPartition(io.RawIOBase):
    def __init__(self, disk, offset, size):
        self.disk, self.offset, self.size, self.pos = disk, offset, size, 0
    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos
    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        if self.pos < 0: raise ValueError('negative offset')
        return self.pos
    def read(self, size=-1):
        if size < 0: size = self.size - self.pos
        size = min(size, self.size - self.pos)
        if size <= 0: return b''
        absolute = self.offset + self.pos
        aligned = absolute // 512 * 512
        shift = absolute - aligned
        length = ((shift + size + 511) // 512) * 512
        self.disk.seek(aligned)
        result = self.disk.read(length)[shift:shift + size]
        self.pos += len(result)
        return result
    def readinto(self, buffer):
        result = self.read(len(buffer)); buffer[:len(result)] = result; return len(result)

if __name__ == '__main__':
    out = BASE / 'card-inventory'
    out.mkdir(exist_ok=True)
    with open(r'\\.\PhysicalDrive2', 'rb', buffering=0) as disk:
        mbr = disk.read(512)
        if mbr[510:512] != b'\x55\xaa' or struct.unpack_from('<I', mbr, 440)[0] != 0xff57595b:
            raise RuntimeError('Card MBR does not match the verified Pi boot configuration')
        start, sectors = struct.unpack_from('<II', mbr, 446 + 16 + 8)
        if start * 512 != 545259520: raise RuntimeError('Unexpected root partition')
        fs = ExtFS(CardPartition(disk, start * 512, sectors * 512))
        print('Root filesystem:', fs.volume_name, fs.uuid)
        if len(sys.argv) > 1:
            for path in sys.argv[1:]:
                try:
                    node = fs.get(path)
                    if node.filetype == 0o040000:
                        print(path, sorted(node.listdir()))
                    else:
                        content = node.open().read()
                        target = out / path.strip('/').replace('/', '__')
                        target.write_bytes(content)
                        print('Saved', path, 'bytes', len(content))
                except Exception as error: print(path, type(error).__name__, str(error))
            sys.exit(0)
        for path in ['/usr/lib/os-release', '/etc/hostname', '/etc/passwd', '/var/lib/dpkg/status',
                     '/usr/sbin/rpi-usb-gadget', '/etc/ssh/ssh_host_ed25519_key.pub',
                     '/usr/share/keyrings/debian-archive-keyring.gpg', '/etc/apt/sources.list',
                     '/etc/apt/sources.list.d/debian.sources', '/etc/apt/sources.list.d/raspi.sources']:
            try:
                content = fs.get(path).open().read()
                (out / path.strip('/').replace('/', '__')).write_bytes(content)
                if path in ['/usr/lib/os-release', '/etc/hostname'] or '/etc/apt/' in path:
                    print(path, content.decode(errors='replace').strip())
                elif path == '/etc/passwd':
                    users = [line.split(':') for line in content.decode().splitlines() if 1000 <= int(line.split(':')[2]) < 65534]
                    print('Login users:', [{'name': u[0], 'uid': u[2], 'home': u[5], 'shell': u[6]} for u in users])
                elif path == '/var/lib/dpkg/status':
                    installed = {p['Package']: p for p in Deb822.iter_paragraphs(content.decode()) if p.get('Status') == 'install ok installed'}
                    for package in ['mumble', 'mumble-server', 'rpi-usb-gadget', 'openssh-server', 'network-manager', 'systemd', 'cloud-init', 'python3']:
                        print(package, installed.get(package, {}).get('Version', 'not installed'))
                    print('Installed package count:', len(installed))
            except Exception as error:
                print(path, type(error).__name__, str(error))
        for path in ['/usr/lib/systemd/system-generators/systemd-run-generator', '/etc/NetworkManager/system-connections']:
            try: print(path, 'present', fs.get(path).size)
            except Exception: print(path, 'not present')
