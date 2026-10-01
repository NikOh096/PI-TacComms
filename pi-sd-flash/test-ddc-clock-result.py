import fcntl
import functools
import operator
import os
from pathlib import Path
import subprocess
import time

frequency = int.from_bytes(Path('/sys/firmware/devicetree/base/soc/i2c@7ef04500/clock-frequency').read_bytes(), 'big')
print('HDMI control bus frequency:', frequency, flush=True)
subprocess.run(['systemctl','is-active','mumble-server.service'], check=True)
subprocess.run(['systemctl','stop','halow-console.service'], check=True)
try:
    fd = os.open('/dev/i2c-20', os.O_RDWR)
    try:
        fcntl.ioctl(fd, 0x0703, 0x50)
        os.write(fd, b'\x00')
        edid = os.read(fd, 128)
        print('EDID bytes:', len(edid), 'checksum:', sum(edid) % 256, 'header:', edid[:8].hex(), flush=True)
        fcntl.ioctl(fd, 0x0703, 0x37)
        for host in (0x51, 0x50):
            for label, body in [('power', [0x01, 0xD6]), ('capabilities', [0xF3, 0x00, 0x00])]:
                data = bytes([host, 0x80 | len(body), *body])
                data += bytes([functools.reduce(operator.xor, data, 0x6E)])
                time.sleep(.1)
                count = os.write(fd, data)
                time.sleep(.1)
                response = os.read(fd, 32)
                print(hex(host), label, 'sent:', data.hex(), 'written:', count, 'response:', response.hex(), flush=True)
    finally:
        os.close(fd)
finally:
    subprocess.run(['systemctl','start','halow-console.service'], check=True)
print(subprocess.check_output(['vcgencmd','get_throttled'], text=True).strip(), flush=True)
