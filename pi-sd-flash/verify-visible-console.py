from pathlib import Path
import os
import select
import struct
import subprocess
import time

def pid():
    return subprocess.check_output(['systemctl', 'show', 'mumble-server.service', '-p', 'MainPID', '--value'], text=True).strip()

server_pid = pid()
assert server_pid != '0'
subprocess.run(['systemctl', 'restart', 'halow-console.service'], check=True)
deadline = time.monotonic() + 25
while time.monotonic() < deadline:
    screen = Path('/dev/vcs1').read_bytes().decode('ascii', errors='replace')
    if 'HALOW VOICE' in screen and 'timeout disabled' in screen:
        print('Status view restored. Checking 70 seconds of continued visibility; touch input is also being observed.', flush=True)
        break
    time.sleep(1)
else:
    raise RuntimeError('Status view did not reappear')

inputs = []
for path in Path('/sys/class/input').glob('event*/device/name'):
    if 'ADS7846' in path.read_text():
        inputs.append(os.open('/dev/input/' + path.parents[1].name, os.O_RDONLY | os.O_NONBLOCK))
event = struct.Struct('qqHHi')
end = time.monotonic() + 70
presses = 0
try:
    while time.monotonic() < end:
        ready, _, _ = select.select(inputs, [], [], min(1, max(0, end - time.monotonic())))
        for fd in ready:
            payload = os.read(fd, event.size * 64)
            for offset in range(0, len(payload) - event.size + 1, event.size):
                _, _, kind, code, value = event.unpack_from(payload, offset)
                if kind == 1 and code == 330 and value == 1:
                    presses += 1
                    print('Touch press detected:', presses, flush=True)
finally:
    for fd in inputs:
        os.close(fd)

screen = Path('/dev/vcs1').read_bytes().decode('ascii', errors='replace')
assert 'HALOW VOICE' in screen and 'timeout disabled' in screen
assert pid() == server_pid, 'Mumble unexpectedly restarted during the console test'
print('PASS: console text remains present beyond 60 seconds; Mumble process was uninterrupted.', flush=True)
print('Observed touch presses:', presses, flush=True)
subprocess.run(['systemctl', 'is-active', 'mumble-server.service', 'halow-console.service'], check=True)
subprocess.run(['vcgencmd', 'get_throttled'], check=True)
