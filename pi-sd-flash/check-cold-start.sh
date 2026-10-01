set -eu
systemctl restart halow-console.service
systemctl is-active mumble-server.service halow-console.service
systemctl is-enabled mumble-server.service halow-console.service
vcgencmd get_throttled
ip -4 -o addr show dev eth0
grep -iE 'ads7846|spi' /proc/interrupts || true
cat /sys/class/input/event4/device/name
pinctrl get 7-11,25
journalctl -b -k --no-pager | grep -iE 'ads7846|touch' || true
