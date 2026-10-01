# Recovery status

Update 2026-09-29: the Pi booted successfully without reflashing. USB SSH, Mumble and the secure touchscreen services recovered. The screen service Wants change is installed. Both HD01s are now paired to TC-HTRT01, and Pixel Mumble authentication through TC-HTHD02 succeeded. See PHONE-CONNECTION-GUIDE.md for current network names and addresses. The latest power flags are 0x50000: undervoltage/throttling occurred earlier in this boot, with no current undervoltage/throttling bits set. The incident and card inspection notes below are historical.

The Pi became unreachable after the USB splitter/cable change. Windows reports its Raspberry Pi USB network device absent even after a device rescan. The user now reports HDMI "No signal", a steady red PWR LED and a blinking green ACT LED. These observations do not establish SD corruption.

The phone successfully joined the H7608's ordinary Wi-Fi at 10.42.0.162. A ping to the Pi's reserved Ethernet address, 10.42.0.137, returned host unreachable. The browser-based DHCP check did not complete. The phone subsequently disconnected from ADB, so the attempted return to HD01 Wi-Fi could not be performed. Its last verified Wi-Fi was WHL-AP-72AA.

## Verified recovery material on this PC

- `raspios-trixie-arm64-verified.img.xz`: original Raspberry Pi OS installer image, **not an image of the configured Pi**.
- `backup-2026-09-28/`: original boot configuration files.
- `halow-setup/`: provisioning code and offline packages.
- `taccomms-admin/`: current touchscreen/backend source and service units.
- `display-power/halow-ddc-slow.dts`: source of the working display power-control overlay.
- `private/`: existing credentials, SSH key and dongle configuration backups; do not print contents.

There is no complete configured-card image in this task's local files. A new protected recovery backup has now been captured from the card at `private/recovery-20260928-235556/`. It includes `/etc`, TacComms code/state/PIN hashes, calibration, Mumble database, SSH authorization, NetworkManager state, logs, earlier on-card backups and a raw copy of the entire boot partition. All 1,092 regular files in the archive passed SHA256 read-back checks, with no read errors; the Mumble SQLite integrity check returned `ok`. The archive preserves Linux modes, owner IDs and symbolic links. Do not print secret contents.

An earlier recovery directory is an incomplete attempt; use the exact directory recorded in `recovery-latest.json`.

## Inspection results

- Identified card: USB disk 2 at inspection, 125,671,833,600 bytes; MBR signature `ff57595b`; root UUID `7695adc1-3681-459a-894f-80f1b615d430`.
- Read-only Windows CHKDSK of bootfs found no filesystem problems.
- All 41 original boot firmware/kernel/initramfs files match the saved, verified Raspberry Pi OS installer.
- Root filesystem metadata reports zero recorded filesystem errors. Critical configuration and recovery directories are readable. This is **not a complete ext4 fsck or a full-card surface test**.
- PIN JSON has both admin and recovery records; calibration JSON is readable; emergency state is false.
- No repair, reflash, configuration change or filesystem write was requested by our inspection scripts. The source card was opened read-only.
- User raised the possibility that the PiSugar battery was depleted. Stable power should be tested before invasive repairs.

## Historical recovery plan (completed)

Safely eject the unchanged card, return it to the fully powered-off Pi, and retry with stable power. Charge the PiSugar through its own USB charging input using a suitable 5 V supply; its official specification is 5 V / 3 A maximum input. A PC connection to the Pi itself does not charge the PiSugar battery. Once power/boot is restored, check USB SSH, Mumble, display and undervoltage flags; apply the pending screen service Wants change. Identify removable disks afresh on every future recovery operation.

At the time of inspection, HaLow pairing was pending after a safe rollback. The later pairing and credential changes were completed and verified over the restored Pi management path.
