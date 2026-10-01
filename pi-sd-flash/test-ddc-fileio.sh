set -u
systemctl stop halow-console.service
TERM=linux setterm --blank poke < /dev/tty1 > /dev/tty1
ddcutil --bus 20 --skip-ddc-checks --use-file-io --disable-dynamic-sleep --sleep-multiplier 4 getvcp D6
ddcutil --bus 20 --skip-ddc-checks --use-ioctl-io --disable-dynamic-sleep --sleep-multiplier 4 getvcp D6
systemctl start halow-console.service
