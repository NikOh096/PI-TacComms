"""Read-only inventory for the proposed TacComms audio processing path."""
import json
import shutil
import subprocess
from pathlib import Path

def output(*args):
    result = subprocess.run(args, text=True, capture_output=True, timeout=20)
    return result.stdout.strip() or result.stderr.strip()

report = {
    'model': Path('/proc/device-tree/model').read_text().rstrip('\0'),
    'architecture': output('uname', '-m'),
    'cpus': output('getconf', '_NPROCESSORS_ONLN'),
    'memory': output('free', '-m'),
    'disk': output('df', '-h', '/'),
    'power': output('vcgencmd', 'get_throttled'),
    'compiler': shutil.which('cc'),
    'cmake': shutil.which('cmake'),
    'pkg_config': shutil.which('pkg-config'),
    'packages': output('dpkg-query', '-W', '-f=${binary:Package} ${Version}\n',
                       'mumble-server', 'libopus*', 'librnnoise*', 'libspeexdsp*',
                       'qtbase5-dev', 'libprotobuf-dev', 'libzeroc-ice-dev'),
    'candidate_packages': output('apt-cache', 'policy', 'librnnoise-dev', 'libopus-dev'),
    'mumble_status': output('systemctl', 'show', 'mumble-server.service',
                            '-p', 'ActiveState', '-p', 'MainPID', '-p', 'NRestarts'),
}
print(json.dumps(report, indent=2))
