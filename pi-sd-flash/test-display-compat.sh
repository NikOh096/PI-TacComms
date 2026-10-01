set -u
systemctl stop halow-console.service
TERM=linux setterm --blank poke < /dev/tty1 > /dev/tty1
ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --disable-dynamic-sleep --sleep-multiplier 2 getvcp D6 --verbose
ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --noverify setvcp D6 1
systemctl start halow-console.service
