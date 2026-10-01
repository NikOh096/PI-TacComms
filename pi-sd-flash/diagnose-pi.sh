set -eu
date -u
vcgencmd get_throttled
cat /proc/sys/kernel/printk
printf '\nAPT dry run without no-download:\n'
apt-get --simulate --no-remove --no-install-recommends install /var/lib/halow-setup/debs/*.deb
printf '\nDisplay and touch:\n'
cat /sys/class/graphics/fb0/virtual_size
stty -F /dev/tty1 size
cat /proc/bus/input/devices
printf '\nPower and GPIO:\n'
ls /sys/class/power_supply
command -v pinctrl || true
