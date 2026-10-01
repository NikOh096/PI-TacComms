# OSOYOO HDMI35 V2.0 backlight control

This Pi 4B's screen returned malformed DDC replies at the default HDMI control-clock frequency of 97,500 Hz. Reducing that clock to 50,000 Hz restored readable capabilities and power status. Both settings are supported by the Raspberry Pi HDMI I2C driver.

The successful direct hardware test used D6=3 to suspend the monitor and D6=1 to wake it. The user confirmed the backlight went completely dark and a stylus tap restored the picture. Linux recorded the touch event while the monitor was suspended. The Pi and its Mumble server continued running.

After installing the console integration, the normal 60-second timer was also tested. It logged `Display suspended`, the screen reported power state `0x03`, and Mumble's process ID stayed unchanged.

The setting affects HDMI-A-1's low-speed control channel only. It does not change the screen's pixel clock, resolution, SPI touch controller, or battery-sensor GPIO assignments.

## Installed configuration

- `/boot/firmware/overlays/halow-ddc-slow.dtbo`: compiled from the adjacent source file.
- `/boot/firmware/config.txt`: active `[all]` section contains `dtoverlay=halow-ddc-slow`.
- `/boot/firmware/config.txt.before-halow-ddc-clock-test`: configuration backup from before this change.
- `/usr/local/bin/halow-console`: uses a 60-second inactivity timer, reads touchscreen events, and sends the verified power commands.
- `halow-console.service`: enabled at startup. Its journal records `Display suspended` and `Display awake`.

The clock change was activated by reboot and read back from the live device tree as 50,000 Hz. The console's working DDC command options are:

```bash
ddcutil --bus 20 --skip-ddc-checks --mccs 2.2 --disable-dynamic-sleep --sleep-multiplier 2 getvcp D6
```

Replace `getvcp D6` with `setvcp D6 3` for suspend or `setvcp D6 1` for wake. The console discovers the connected HDMI bus dynamically rather than relying on bus 20 remaining its number.

If display power control fails in the future, the console keeps status visible instead of drawing black or removing the HDMI signal. This is a recovery behavior, not a power-saving mode.

## Rebuilding the overlay

On the Pi, with `dtc` installed:

```bash
dtc -@ -I dts -O dtb -o halow-ddc-slow.dtbo halow-ddc-slow.dts
```

Copy the result into `/boot/firmware/overlays/`, add the overlay line once under `[all]`, and reboot. These steps are already complete on the current card.

## References

- [OSOYOO DDC power commands](https://osoyoo.com/2023/08/06/osoyoo-3-5-inch-hdmi-screen-v1-2-ddc-ci-function/)
- [Raspberry Pi HDMI I2C driver and supported clock frequencies](https://github.com/raspberrypi/linux/blob/rpi-6.18.y/drivers/i2c/busses/i2c-brcmstb.c)
