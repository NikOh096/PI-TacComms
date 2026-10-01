from pathlib import Path
import os
import subprocess

config = Path('/boot/firmware/config.txt')
saved = Path('/boot/firmware/config.txt.before-halow-ddc-clock-test')
text = config.read_text()
marker = '# HaLow reversible HDMI DDC timing test'
if marker in text:
    raise RuntimeError('Timing test is already installed; inspect before changing it again')
if saved.exists():
    raise RuntimeError('An earlier timing-test backup exists; inspect before overwriting')
saved.write_bytes(config.read_bytes())
source = Path('/var/lib/halow-setup/halow-ddc-slow.dts')
source.write_text('''/dts-v1/;
/plugin/;
/ {
    compatible = "brcm,bcm2711";
    fragment@0 {
        target = <&ddc0>;
        __overlay__ { clock-frequency = <50000>; };
    };
};
''')
target = Path('/boot/firmware/overlays/halow-ddc-slow.dtbo')
subprocess.run(['dtc', '-@', '-I', 'dts', '-O', 'dtb', '-o', str(target), str(source)], check=True)
assert target.stat().st_size > 100
config.write_text(text.rstrip() + '\n\n[all]\n' + marker + '\ndtoverlay=halow-ddc-slow\n')
os.sync()
print('Prepared 50 kHz HDMI-A-1 control bus test; backup saved at', saved)
print('Only the display control clock changes. USB management and Ethernet settings are unchanged.')
print('Reboot not yet issued.')
