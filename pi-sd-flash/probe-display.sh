set -u
systemctl stop halow-console.service
TERM=linux setterm --blank poke < /dev/tty1 > /dev/tty1
ddcutil --bus 20 --sleep-multiplier 2 getvcp D6
ddcutil --bus 20 detect --verbose
pinctrl get 3
vcgencmd get_throttled
systemctl start halow-console.service
