"""Compare captured Pi firmware files against the verified original installer."""
import hashlib, json, lzma, re, struct, tarfile
from pathlib import Path
base = Path(__file__).resolve().parent
directory = Path(json.loads((base / 'recovery-latest.json').read_text())['directory'])
original = directory / 'original-boot-partition.img'
if not original.exists():
    with lzma.open(base / 'raspios-trixie-arm64-verified.img.xz', 'rb') as source, original.open('wb') as target:
        mbr = source.read(512)
        first, count = struct.unpack_from('<II', mbr, 454)
        source.seek(first * 512)
        remaining = count * 512
        while remaining:
            data = source.read(min(4 * 1024 * 1024, remaining))
            assert data
            target.write(data)
            remaining -= len(data)

class Fat:
    def __init__(self, path):
        self.f = path.open('rb')
        b = self.f.read(512)
        self.bps = struct.unpack_from('<H', b, 11)[0]
        self.spc = b[13]
        self.reserved = struct.unpack_from('<H', b, 14)[0]
        self.nfat = b[16]
        self.fatsz = struct.unpack_from('<I', b, 36)[0]
        self.root = struct.unpack_from('<I', b, 44)[0]
        assert self.bps == 512 and b[510:] == b'\x55\xaa'
        self.f.seek(self.reserved * self.bps)
        self.fat = self.f.read(self.fatsz * self.bps)
        self.data = (self.reserved + self.nfat * self.fatsz) * self.bps
        self.cluster_size = self.bps * self.spc
    def chunks(self, cluster):
        seen = set()
        while 2 <= cluster < 0x0ffffff8:
            assert cluster not in seen, 'FAT loop'
            seen.add(cluster)
            self.f.seek(self.data + (cluster - 2) * self.cluster_size)
            data = self.f.read(self.cluster_size)
            assert len(data) == self.cluster_size
            yield data
            cluster = struct.unpack_from('<I', self.fat, cluster * 4)[0] & 0x0fffffff
    def files(self):
        names = []
        result = {}
        for block in self.chunks(self.root):
            for offset in range(0, len(block), 32):
                e = block[offset:offset + 32]
                if e[0] == 0: return result
                if e[0] == 0xe5:
                    names = []; continue
                if e[11] == 15:
                    names.insert(0, (e[1:11] + e[14:26] + e[28:32]).decode('utf-16le'))
                    continue
                name = ''.join(names).split('\x00')[0].rstrip('\uffff') if names else e[:8].decode().rstrip() + ('.' + e[8:11].decode().rstrip() if e[8:11].strip() else '')
                names = []
                if e[11] & 0x18: continue
                cluster = (struct.unpack_from('<H', e, 20)[0] << 16) | struct.unpack_from('<H', e, 26)[0]
                size = struct.unpack_from('<I', e, 28)[0]
                digest = hashlib.sha256()
                remaining = size
                for data in self.chunks(cluster):
                    digest.update(data[:remaining])
                    remaining -= min(len(data), remaining)
                    if not remaining: break
                assert remaining == 0, name
                result[name.lower()] = digest.hexdigest()
        return result

before = Fat(original).files()
current = Fat(directory / 'boot-partition.img').files()
names = [n for n in before if n.endswith(('.elf', '.dat', '.dtb', '.img', '.bin')) or n.startswith('initramfs')]
bad = [n for n in names if current.get(n) != before[n]]
print('Original firmware/kernel/initramfs files compared:', len(names))
print('Mismatches:', bad)
with tarfile.open(directory / 'taccomms-recovery.tar.gz', 'r:gz') as archive:
    for path in ('var/log/boot.log', 'var/log/boot.log.1'):
        text = archive.extractfile(path).read().decode(errors='replace')
        text = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text)
        print(path, 'last lines:\n' + '\n'.join(text.splitlines()[-65:]))
(directory / 'boot-verification.json').write_text(json.dumps({'compared': names, 'mismatches': bad}, indent=2))
assert not bad, 'Boot file mismatch requires investigation'
