import fcntl
import functools
import operator
import os
from pathlib import Path
import subprocess
import time
subprocess.run(['systemctl', 'stop', 'halow-console.service'], check=True)
try:
    fd = os.open('/dev/i2c-20', os.O_RDWR)
    fcntl.flock(fd, fcntl.LOCK_EX)
    fcntl.ioctl(fd, 0x0703, 0x37)
    for feature in (0xD6, 0x10, 0xDF):
        packet = bytes([0x51, 0x82, 0x01, feature])
        packet += bytes([functools.reduce(operator.xor, packet, 0x6E)])
        os.write(fd, packet)
        time.sleep(0.2)
        response = os.read(fd, 11)
        print(hex(feature), response.hex())
        time.sleep(0.2)
    os.close(fd)
finally:
    subprocess.run(['systemctl', 'start', 'halow-console.service'], check=True)
