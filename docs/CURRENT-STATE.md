# Current state at the October 1, 2026 source export

The latest user report was that everything works. Last detailed machine checks
were September 29. USB SSH timed out during this export; no current live files,
PINs, phone settings, or services were changed while preparing the repository.

## Installed and previously verified

- Original Debian Mumble 1.5.735-5+deb13u1, unattended startup, local voice network.
- Cyan TacComms touchscreen, tap-to-cycle Status/Logs/Processes, Admin and Lock
  buttons, on-screen keyboard, two separate six-digit PINs enrolled on the Pi.
- Lock confirmation and persistent emergency lock; calls continue; recovery
  PIN unlocks emergency mode, normal admin access still needs the admin PIN.
- PIN hashing/rate limits, restricted backend socket, command allowlist.
- USB-only key-based SSH, local-interface voice firewall, authenticated Ice on
  127.0.0.1:6502, unused services and alternate console login disabled.
- 60-second inactivity sleep using HDMI DDC D6=3 and wake D6=1 with a 50 kHz
  control-clock overlay. Owner confirmed dark backlight and stylus wake in the
  hardware test. Later UI-specific physical checks were not all independently
  recorded, so inspect actual behavior before claiming new validation.
- Gateway and both HD01 names/reservations, US radio configuration, DHCP bridge
  topology. Pixel login through TC-HTHD02; matching server certificate reached
  through TC-HTHD01. The authenticated session used TCP fallback. An instrumented
  two-phone conversation/HaLow UDP test was not recorded before the user's
  subsequent report that everything works.
- Persistent journal, 30-second health monitor, `health` and `crashlog` commands.
- Screen startup waits for the admin socket for up to 30 seconds. Only public
  state queries retry; administrative commands are never automatically replayed.

## Undervoltage investigation

Read [the incident report](../pi-sd-flash/CRASH-REPORT-2026-09-29.md). Two current-boot
undervoltage episodes lasted 214 and 204 seconds. A prior episode lasted 210
seconds. Flags were 0x50000: historical undervoltage/throttling, not active at
inspection. Mumble, screen, and admin had zero restarts in the inspected two-hour
boot. Earlier reboots exist, but the specific cause of each USB loss is unknown.

The battery connector had been repaired by the owner. Power-path instability is
confirmed; which supply/cable/connector caused it was not established. Investigate
fresh diagnostics before resuming sustained builds. Earlier notes reporting
0x0 flags or no available prior-boot journal predate these findings.

## Still pending

1. Central audio filter: Windows prototype passed local synthetic/core/load tests.
   The isolated Pi build stopped at step 23/42 after a USB disconnect. Pi core,
   load, encrypted UDP/TCP integration, deployment, and real headset testing
   remain. Do not report this feature installed.
2. Local `taccomms-admin/backend.py` includes noise-control commands; live code
   received only targeted diagnostics/startup patches. Never deploy the local
   admin directory as an exact image of production.
3. Battery percentage needs a physical gauge such as the proposed MAX17048.
   The S Plus has no supported built-in percentage reading in this setup.
4. Headset model and final real-audio testing remain open. Product examples were
   discussed; none should be treated as confirmed hardware.
5. The old phone developer stay-awake setting was temporarily 15, originally 0.
   Restoration was not recorded. Check current owner preference before changing
   a newer setting. **Mobile data was restored and confirmed active; keep it on.**

## Historical-file caveats

`START-HERE.txt`, `DESIGN.md`, `TACCOMMS-UPDATE.md`, display-power notes, and
noise `RESUME.md` preserve the sequence of work. Earlier mentions of disabled
HaLow, legacy `halow-console`, five-tap locking, a disconnected phone, or Ethernet
without carrier are historical observations, not current prescriptions.
`modern-inputs.json` and admin manifests are historical hashes; regenerate source
bundles/manifests after changes. No private recovery image or database is included.
