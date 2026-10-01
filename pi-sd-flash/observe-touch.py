import glob
import os
import select
import struct
import time

event = struct.Struct('qqHHi')
inputs = {}
for path in glob.glob('/dev/input/event*'):
    name_path = '/sys/class/input/' + path.rsplit('/', 1)[1] + '/device/name'
    name = open(name_path).read().strip()
    print(path, name, flush=True)
    if 'ADS7846' in name:
        inputs[os.open(path, os.O_RDONLY | os.O_NONBLOCK)] = path
print('Listening to touchscreen for 40 seconds...', flush=True)
end = time.monotonic() + 40
count = 0
try:
    while inputs and time.monotonic() < end:
        ready, _, _ = select.select(list(inputs), [], [], min(1, max(0, end - time.monotonic())))
        for fd in ready:
            data = os.read(fd, event.size * 64)
            for offset in range(0, len(data), event.size):
                _, _, kind, code, value = event.unpack(data[offset:offset + event.size])
                if kind == 1:
                    count += 1
                    print('TOUCH KEY', code, value, flush=True)
    print('Touch key events:', count, flush=True)
finally:
    for fd in inputs:
        os.close(fd)
