# TacComms incident report — September 29, 2026

The displayed two-hour uptime is correct. The Pi was reachable over USB when
checked, with 7,295 seconds of uptime (2 h 1 min) and boot ID
`4a7ea844-e192-4ed8-b2e1-75dff6b763b9`.

## Confirmed findings

- The current boot recorded two kernel **“Undervoltage detected!”** events.
  - At uptime 37 min 39 sec; voltage normalised at 41 min 13 sec (214 seconds).
  - At uptime 81 min 30 sec; voltage normalised at 84 min 54 sec (204 seconds).
- Current firmware flags were `0x50000`: undervoltage and throttling occurred
  earlier in this boot; neither was active at the time of inspection.
- Mumble, the administration service and the touchscreen were all active with
  **zero service restarts in this boot**. CPU temperature was 38.9 C and roughly
  3.5 GiB of memory was available.
- Eight boot IDs have been preserved since persistent logging was enabled.
  The current two-hour boot does not erase the earlier reboot history. Several
  earlier boots ended without a recorded orderly shutdown, including three that
  stopped logging around 11 seconds after startup. Manual power cycling could
  also produce these records.
- A preceding boot recorded another undervoltage episode lasting 210 seconds.
- The reviewed kernel logs contain no matching kernel panic, out-of-memory kill,
  watchdog reset, MMC error/timeout, or EXT4 error. A sudden loss of power can
  still prevent a final error from being recorded.
- USB was configured and reachable during inspection. Ethernet had no carrier.

## Interpretation

Power instability is confirmed and is the strongest lead for the interruptions.
The logs do not identify whether the PC USB supply, cable, PiSugar battery path,
or repaired connector caused it. They also do not establish that every earlier
USB disconnection was a full Pi crash.

My earlier explanation should have distinguished a lost SSH/USB connection from
a confirmed reboot. Boot IDs now establish that earlier reboots occurred, while
the present boot has remained up for about two hours.

## Installed diagnostics

Use `health` or `crashlog` in the PIN-protected Admin console. Boot logs survive
restart, and power, temperature, memory, services and USB state are sampled every
30 seconds. The touchscreen's missing-admin-socket startup error has been fixed.

The full private report is saved on this PC at
`pi-sd-flash/private/diagnostics-20260929-063216.json` and on the Pi at
`/var/lib/taccomms-diagnostics/latest-report.json`.

The central noise filter remains an uninstalled prototype. Compilation and
deployment should wait until the power path is stable. No Mumble server crash
was found in the current boot.
