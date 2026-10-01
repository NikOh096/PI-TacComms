set -u
ddcutil detect --verbose
printf '\nBacklight interfaces:\n'
ls /sys/class/backlight
printf '\nHDMI identity:\n'
python3 - <<'PY'
from pathlib import Path
for p in Path('/sys/class/drm').glob('card*-HDMI-A-*/edid'):
    raw = p.read_bytes()
    if not raw:
        continue
    print(p, len(raw), raw.hex())
    for offset in (54,72,90,108):
        block=raw[offset:offset+18]
        if block[:3]==b'\0\0\0':
            print('descriptor', block[3], repr(block[5:].decode('ascii',errors='replace')))
PY
printf '\nConsole recent log:\n'
journalctl -b -u halow-console.service --no-pager -n 12
