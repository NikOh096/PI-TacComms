import fcntl
import functools
import operator
import os
from pathlib import Path
import select
import struct
import subprocess
import time

subprocess.run(['systemctl', 'stop', 'halow-console.service'], check=True)
fd = os.open('/dev/i2c-20', os.O_RDWR)
touch = os.open('/dev/input/event4', os.O_RDONLY | os.O_NONBLOCK)
event = struct.Struct('qqHHi')
def power(value):
    payload = bytes([0x51, 0x84, 0x03, 0xD6, 0, value])
    payload += bytes([functools.reduce(operator.xor, payload, 0x6E)])
    assert os.write(fd, payload) == len(payload)
    time.sleep(0.1)

try:
    fcntl.flock(fd, fcntl.LOCK_EX)
    fcntl.ioctl(fd, 0x0703, 0x37)
    power(1)
    time.sleep(1)
    power(3)
    print('Sent OSOYOO suspend command. Tap screen now; automatic restore after 20 seconds.', flush=True)
    end = time.monotonic() + 20
    touched = False
    while time.monotonic() < end:
        ready, _, _ = select.select([touch], [], [], 0.5)
        if ready:
            payload = os.read(touch, event.size * 64)
            for offset in range(0, len(payload), event.size):
                _, _, kind, code, value = event.unpack_from(payload, offset)
                if kind == 1 and code == 330 and value == 1:
                    touched = True
                    break
        if touched:
            break
    print('Touch event while suspended:', touched, flush=True)
    print('Server:', subprocess.check_output(['systemctl', 'is-active', 'mumble-server.service'], text=True).strip())
finally:
    power(1)
    os.close(fd)
    os.close(touch)
    subprocess.run(['systemctl', 'start', 'halow-console.service'], check=True)
