set -eu
systemctl is-active mumble-server.service || true
systemctl is-active halow-provision.service || true
tail -n 28 /boot/firmware/halow-setup/provision.log
vcgencmd get_throttled
command -v ddcutil || true
for path in /sys/class/drm/card*-HDMI-A-*; do
    printf '%s ' "$path"
    cat "$path/status"
    readlink -f "$path/ddc" || true
done
