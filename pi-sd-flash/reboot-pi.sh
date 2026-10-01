set -eu
systemctl is-enabled mumble-server.service
systemctl is-enabled halow-console.service
sync
systemctl reboot
