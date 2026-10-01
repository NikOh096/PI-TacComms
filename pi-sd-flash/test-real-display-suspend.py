import os
from pathlib import Path
import select
import struct
import subprocess
import time

base = ['ddcutil', '--bus', '20', '--skip-ddc-checks', '--mccs', '2.2', '--disable-dynamic-sleep', '--sleep-multiplier', '2']
def ddc(*args):
    result = subprocess.run(base + list(args), capture_output=True, text=True, timeout=12)
    print(' '.join(args), 'exit', result.returncode, result.stdout.strip(), result.stderr.strip(), flush=True)
    return result.returncode

subprocess.run(['systemctl', 'stop', 'halow-console.service'], check=True)
fds = []
event = struct.Struct('qqHHi')
for path in Path('/sys/class/input').glob('event*/device/name'):
    if 'ADS7846' in path.read_text():
        fds.append(os.open('/dev/input/' + path.parents[1].name, os.O_RDONLY | os.O_NONBLOCK))
try:
    ddc('setvcp', 'D6', '3')
    ddc('getvcp', 'D6')
    print('DISPLAY SUSPEND TEST ACTIVE. Tap with stylus to wake; automatic restore after 60 seconds.', flush=True)
    end = time.monotonic() + 60
    touched = False
    while time.monotonic() < end and not touched:
        ready, _, _ = select.select(fds, [], [], min(1, max(0, end - time.monotonic())))
        for fd in ready:
            payload = os.read(fd, event.size * 64)
            for offset in range(0, len(payload) - event.size + 1, event.size):
                _, _, kind, code, value = event.unpack_from(payload, offset)
                if kind == 1 and code == 330 and value == 1:
                    touched = True
                    print('Physical touch press received while display suspended.', flush=True)
    print('Touch wake event:', touched, flush=True)
finally:
    ddc('setvcp', 'D6', '1')
    for fd in fds:
        os.close(fd)
    subprocess.run(['systemctl', 'start', 'halow-console.service'], check=True)
ddc('getvcp', 'D6')
subprocess.run(['systemctl', 'is-active', 'mumble-server.service'], check=True)
