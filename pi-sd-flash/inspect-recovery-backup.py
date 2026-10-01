import datetime, json, tarfile
from pathlib import Path
base = Path(__file__).resolve().parent
directory = sorted((base / 'private').glob('recovery-*'))[-1]
with tarfile.open(directory / 'taccomms-recovery.tar.gz', 'r:gz') as archive:
    members = {m.name: m for m in archive}
    def read(path):
        return archive.extractfile(members[path]).read().decode(errors='replace')
    print('Backup:', directory.name)
    print('fstab:', read('etc/fstab'))
    print('Log files:', [p for p in members if p.startswith('var/log/') and members[p].isfile()])
    print('Relevant service links:')
    for path, item in members.items():
        if path.startswith('etc/systemd/system/') and item.issym() and any(v in path.lower() for v in ('taccomms', 'mumble', 'halow', 'usb', 'network', 'ssh', 'default.target')):
            print(path, '->', item.linkname)
    print('USB-related configuration files:', [p for p in members if p.startswith('etc/') and any(v in p.lower() for v in ('gadget', 'usb', 'modules-load'))])
    for path in ('etc/modules-load.d/usb-gadget.conf', 'etc/systemd/system/taccomms-screen.service',
                 'etc/systemd/system/taccomms-admin.service', 'etc/systemd/system/halow-provision.service'):
        if path in members and members[path].isfile(): print(path + '\n' + read(path))
    for path in ('var/lib/taccomms/pins.json', 'var/lib/taccomms-ui/touch.json'):
        value = json.loads(read(path))
        print(path, 'valid JSON, fields:', list(value))
    print('Security state:', json.loads(read('var/lib/taccomms/security-state.json')))
    print('TacComms file modification times:')
    for path, item in members.items():
        if path.startswith('opt/taccomms/') and item.isfile():
            print(path, item.size, datetime.datetime.fromtimestamp(item.mtime, datetime.timezone.utc).isoformat())
