set -u
uname -a
systemctl stop halow-console.service
TERM=linux setterm --blank poke < /dev/tty1 > /dev/tty1
ddcutil --bus 20 getvcp D6
ddcutil detect --verbose
printf '\nHDMI I2C driver:\n'
readlink -f /sys/bus/i2c/devices/i2c-20/device/driver
journalctl -b -k --no-pager | grep -E -i 'i2c|hdmi|voltage' | tail -n 25
systemctl start halow-console.service
