set -eu
systemctl reset-failed halow-provision.service
systemctl start --no-block halow-provision.service
pinctrl get 3
vcgencmd get_throttled
