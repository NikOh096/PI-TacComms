set -u
systemctl stop halow-console.service
trap 'systemctl start halow-console.service' EXIT
ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --disable-dynamic-sleep --sleep-multiplier 2 --ddc getvcp D6
ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --disable-dynamic-sleep --sleep-multiplier 2 --ddc getvcp DF
ddcutil --bus 20 --skip-ddc-checks --disable-dynamic-sleep --sleep-multiplier 2 capabilities
