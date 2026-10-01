set -u
systemctl stop halow-console.service
trap 'systemctl start halow-console.service' EXIT
TERM=linux setterm --blank poke < /dev/tty1 > /dev/tty1
timeout 15 ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --disable-dynamic-sleep --ddc getvcp D6
printf '\nHDMI kernel bus properties:\n'
python3 - <<'PY'
from pathlib import Path
root = Path('/sys/bus/i2c/devices/i2c-20')
print('Name:', (root / 'name').read_text().strip())
node = (root / 'device/of_node').resolve()
print('Node:', node)
for name in ('compatible', 'clock-frequency', 'brcm,clk-freq'):
    path = node / name
    if path.exists(): print(name, path.read_bytes().hex())
PY
systemctl is-active mumble-server.service
