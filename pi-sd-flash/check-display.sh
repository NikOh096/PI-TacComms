set -eu
ddcutil --bus 20 getvcp D6
ddcutil --bus 20 getvcp 10
pinctrl get 3
journalctl -b -u halow-console.service --no-pager -n 14
systemctl is-enabled mumble-server.service
