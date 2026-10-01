# PI-TacComms

Dedicated local voice communications using a Raspberry Pi 4B Mumble server,
a Heltec HT-H7608 gateway, HD01 HaLow nodes, and Android phones running Mumla.
The Pi starts the server automatically and provides a PIN-protected touchscreen
with status, logs, processes, administration, and emergency locking.

**Start a Codex continuation with [codex-handoff.json](codex-handoff.json).**
Then read [current state](docs/CURRENT-STATE.md) and
[new-machine setup](docs/NEW-MACHINE.md).

This repository preserves the project source and operational knowledge. It is
not an SD-card image, a private configuration backup, or a one-command installer.
The existing Pi does not need to be reflashed to continue development.

## System

```text
Bluetooth headset -> Android/Mumla -> HD01 Wi-Fi -> HaLow
    -> TC-HTRT01 gateway -> Ethernet -> Pi/Mumble
```

| Device | Name | Address |
| --- | --- | --- |
| Gateway | TC-HTRT01 | 10.42.0.1 |
| HD01 node 1 | TC-HTHD01 | 10.42.0.160 |
| HD01 node 2 | TC-HTHD02 | 10.42.0.161 |
| Pi, voice interface | halow-pi / TacComms | 10.42.0.137:64738 TCP/UDP |
| Pi, USB management | niko, key-based SSH | 10.12.194.1 |

The gateway supplies DHCP. HD01s are client bridges with DHCP disabled. Region
is United States; HaLow channel 25, 914.5 MHz, 1 MHz width. Voice stays local;
the PC and internet are unnecessary for normal operation. **Keep phone mobile
data enabled.** Accept Android's option to remain on Wi-Fi without internet.

## Contents

- [Phone checklist](docs/PHONE-CHECKLIST.md): add another phone to existing nodes.
- `pi-sd-flash/taccomms-admin/`: touchscreen, PIN security, command backend,
  services, and tests. Local backend includes uninstalled audio-control work.
- `pi-sd-flash/taccomms-diagnostics/`: bounded persistent logging and crash reports.
- `pi-sd-flash/display-power/`: working backlight suspend/wake and DDC overlay.
- `pi-sd-flash/battery-sensor/`: proposed MAX17048 gauge wiring and reader.
- `pi-sd-flash/noise-suppression/`: central filter prototype, pinned dependencies,
  synthetic fixture seed/results, isolated tests, and guarded installer.
- `pi-sd-flash/halow-setup/`: original provisioning source and package metadata.
- Other `pi-sd-flash/` scripts: development, investigation, deployment, and recovery
  history. Many intentionally target the original hardware and require review.

## Current status

The user reported the system working after the September 29 investigation.
Mumble, secure UI, firewall, display sleep, node pairing, and diagnostics were
previously verified. The Pi was unreachable over USB during the October 1
repository preparation, so this export is not a fresh live-device snapshot.

**Central noise suppression is not deployed.** Its Pi build and integration
validation remain unfinished. Battery percentage also requires the proposed
external gauge; PiSugar S Plus alone does not supply that reading in this setup.
See [current state](docs/CURRENT-STATE.md) for evidence and outstanding work.

## Credentials and recovery

Passwords, SSH private keys, PIN state, router exports, journals, device databases,
and SD images are excluded. Transfer the existing `pi-sd-flash/private/` folder
separately using an encrypted channel. Examples under `pi-sd-flash/examples/`
describe required fields without providing working credentials.

Do not regenerate credentials for the existing Pi. Do not reset the working
routers, overwrite PIN state, or run the historical card-flashing scripts.
Read [new-machine setup](docs/NEW-MACHINE.md) before any device operation.

## Local checks

From the repository root, with Python 3.12 or newer:

```sh
python -m unittest discover -s pi-sd-flash/taccomms-admin -p test_security.py -v
python -m unittest discover -s pi-sd-flash/taccomms-diagnostics -p test_diagnostics.py -v
python tools/validate-export.py
```

These do not access or change the Pi. For audio work, follow
[build restoration](docs/BUILD-RESTORATION.md) and the noise-filter handoff.

The repository's existing GPL-3.0 license is preserved. Copied third-party files
retain their own licenses; see [third-party notices](THIRD-PARTY-NOTICES.md).
