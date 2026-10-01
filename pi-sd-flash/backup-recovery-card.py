"""Read-only recovery capture of the positively identified Pi microSD."""
import datetime, hashlib, importlib.util, io, json, os, sqlite3, stat, struct, tarfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('card', BASE / 'inspect-card.py')
card = importlib.util.module_from_spec(spec)
spec.loader.exec_module(card)
destination = BASE / 'private' / ('recovery-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
destination.mkdir()
manifest = {}
errors = []

with open(r'\\.\PhysicalDrive2', 'rb', buffering=0) as disk:
    mbr = disk.read(512)
    assert mbr[510:] == b'\x55\xaa' and struct.unpack_from('<I', mbr, 440)[0] == 0xff57595b
    start, sectors = struct.unpack_from('<II', mbr, 470)
    assert start * 512 == 545259520 and sectors * 512 == 125126574080
    (destination / 'mbr.bin').write_bytes(mbr)
    fs = card.ExtFS(card.CardPartition(disk, start * 512, sectors * 512))
    assert str(fs.uuid) == '7695adc1-3681-459a-894f-80f1b615d430'
    info = {k: getattr(fs.sb, k) for k in ('s_state', 's_errors', 's_error_count', 's_feature_incompat',
             's_mtime', 's_wtime', 's_lastcheck', 's_mnt_count', 's_max_mnt_count',
             's_first_error_time', 's_last_error_time')}
    info.update(uuid=str(fs.uuid), block_size=fs.block_size, blocks=fs.block_count,
                free_blocks=(fs.sb.s_free_blocks_count_hi << 32) | fs.sb.s_free_blocks_count_lo)
    print('Filesystem metadata:', json.dumps(info), flush=True)
    (destination / 'filesystem.json').write_text(json.dumps(info, indent=2))
    roots = ['/etc', '/opt/taccomms', '/usr/local', '/var/lib/taccomms', '/var/lib/taccomms-ui',
             '/var/lib/mumble-server', '/var/lib/halow-setup', '/var/lib/NetworkManager',
             '/home/niko/.ssh', '/var/log', '/var/lib/dpkg/status']
    def add(archive, path, node):
        entry = tarfile.TarInfo(path.lstrip('/'))
        inode = node.inode
        entry.mode = stat.S_IMODE(inode.i_mode)
        entry.uid, entry.gid = inode.i_uid, inode.i_gid
        entry.mtime = inode.i_mtime
        if node.filetype == stat.S_IFDIR:
            entry.type = tarfile.DIRTYPE
            archive.addfile(entry)
            for child in node.iterdir():
                if child.filename not in ('.', '..'):
                    try: add(archive, path + '/' + child.filename, child)
                    except Exception as exc: errors.append({'path': path + '/' + child.filename, 'error': type(exc).__name__})
        elif node.filetype == stat.S_IFLNK:
            entry.type = tarfile.SYMTYPE
            entry.linkname = node.link
            archive.addfile(entry)
            manifest[path] = {'symlink': node.link}
        elif node.filetype == stat.S_IFREG:
            data = node.open().read()
            assert len(data) == node.size, 'Short file read'
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
            manifest[path] = {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    archive_path = destination / 'taccomms-recovery.tar.gz'
    with tarfile.open(archive_path, 'w:gz', compresslevel=1) as archive:
        for path in roots:
            try:
                add(archive, path, fs.get(path))
                print('Backed up:', path, flush=True)
            except Exception as exc: errors.append({'path': path, 'error': type(exc).__name__})
    # Standalone copies used only for diagnostics, in the same protected directory.
    for path in ('/var/lib/mumble-server/mumble-server.sqlite', '/var/lib/taccomms/pins.json',
                 '/var/lib/taccomms/security-state.json', '/var/lib/taccomms-ui/touch.json',
                 '/etc/fstab'):
        (destination / path.strip('/').replace('/', '__')).write_bytes(fs.get(path).open().read())
    print('Backing up complete boot partition...', flush=True)
    disk.seek(8388608)
    remaining = 536870912
    digest = hashlib.sha256()
    with (destination / 'boot-partition.img').open('wb') as target:
        while remaining:
            block = disk.read(min(4 * 1024 * 1024, remaining))
            if not block: raise RuntimeError('Short boot partition read')
            target.write(block)
            digest.update(block)
            remaining -= len(block)
    (destination / 'manifest.json').write_text(json.dumps({'files': manifest, 'errors': errors,
              'boot_sha256': digest.hexdigest()}, indent=2))
    print('Boot partition captured:', digest.hexdigest(), flush=True)

checked = 0
with tarfile.open(archive_path, 'r:gz') as archive:
    for entry in archive:
        if entry.isfile():
            data = archive.extractfile(entry).read()
            assert hashlib.sha256(data).hexdigest() == manifest['/' + entry.name]['sha256']
            checked += 1
db = destination / 'var__lib__mumble-server__mumble-server.sqlite'
with sqlite3.connect(db.as_uri() + '?mode=ro', uri=True) as connection:
    result = connection.execute('PRAGMA integrity_check').fetchall()
    assert result == [('ok',)], 'Mumble database integrity check failed'
print('PASS: Mumble database integrity; verified archived files:', checked, flush=True)
print('Read errors:', json.dumps(errors), flush=True)
print('Recovery directory:', destination, flush=True)
(BASE / 'recovery-latest.json').write_text(json.dumps({'directory': str(destination), 'read_errors': errors}, indent=2))
