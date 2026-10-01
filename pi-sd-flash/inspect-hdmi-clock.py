from pathlib import Path
import subprocess

print('Kernel:', subprocess.check_output(['uname', '-r'], text=True).strip())
for p in Path('/sys/bus/platform/devices').glob('*i2c*'):
    if p.name not in ('fef04500.i2c', 'fef09500.i2c'):
        continue
    node = (p / 'of_node').resolve()
    print('Device:', p.name, 'node:', node)
    for name in ('compatible', 'clock-frequency', 'reg', 'reg-names'):
        prop = node / name
        if prop.exists():
            data = prop.read_bytes()
            print(name, repr(data) if name in ('compatible','reg-names') else data.hex())
print('Device tree DDC symbols:')
for name in ('ddc0', 'ddc1', 'hdmi0', 'hdmi1'):
    prop = Path('/proc/device-tree/__symbols__') / name
    if prop.exists(): print(name, prop.read_bytes().replace(b'\0', b'').decode())
print('Device tree compiler:', subprocess.run(['which','dtc'], capture_output=True, text=True).stdout.strip())
print('HDMI modes and connection:')
for p in Path('/sys/class/drm').glob('card*-HDMI-A-*'):
    print(p.name, (p/'status').read_text().strip())
    print((p/'modes').read_text().strip())
print('Power:', subprocess.check_output(['vcgencmd', 'get_throttled'], text=True).strip())
