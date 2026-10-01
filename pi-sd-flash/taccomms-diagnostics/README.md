# TacComms crash diagnostics

Installed 2026-09-29. In the PIN-protected Admin console:

- `health` shows temperature, power flags, available memory and service restarts.
- `crashlog` saves a report and shows its location.
- `help system` lists these commands with the existing system controls.

The logger starts automatically. It records a health sample every 30 seconds and
saves reports at startup and when power/service state changes. It records boot
identity and uptime as well as wall-clock time, so offline clock corrections do
not hide a reboot. An interrupted boot is reported as an unconfirmed abnormal
shutdown; power loss is not asserted without evidence.

Files on the Pi (root-only):

- `/var/lib/taccomms-diagnostics/latest-report.json`
- `/var/lib/taccomms-diagnostics/last-boot.json`
- `/var/lib/taccomms-diagnostics/health.jsonl` and `health.previous.jsonl`
- `/var/lib/taccomms-diagnostics/reports/` (last 10 reports)
- Persistent system journal under `/var/log/journal/`

Storage is bounded: journal target 128 MiB / 14 days; health history about 4 MiB.
Reports include kernel and service events and any available kernel crash records.
No audio, PINs, passwords or process argument lists are collected by this monitor.
System service logs can contain client names or network addresses, so reports are
kept private. Sudden loss of power may lose the last unsaved events, and some
hardware failures leave no kernel crash record.

Initial findings:

- The vendor `40-rpi-volatile-storage.conf` forced RAM-only journaling. Previous
  boot logs were unavailable. An administrator drop-in now enables persistence.
- The screen crashed once at startup because `/run/taccomms/admin.sock` did not
  exist yet. The screen now waits up to 30 seconds for the public state endpoint;
  no administrative command is automatically replayed.
- After installation: Mumble, Admin and screen were active with zero restarts;
  Mumble's original process continued without interruption. Temperature about
  39 C, power flags `0x0`, about 3.4 GiB RAM available.
- USB was configured. Ethernet showed no physical carrier at the time of the
  report. The Pi's offline clock was about 110 minutes slow and was corrected
  from the PC; its saved systemd clock floor was updated.
- Earlier USB losses remain unexplained because their logs were volatile.

Original files were backed up on the Pi under
`/var/backups/taccomms-diagnostics/20260929-041818/`.
The logger neither reboots the Pi nor changes its firewall or Mumble settings.

An additional USB disconnect occurred during the single-worker build after
logging was installed. Its cause is still unconfirmed and the Pi was unreachable
at the last check. A PC copy is saved at `../private/diagnostics-20260929.json`.
That copy contains 21 samples through 06:17:00 UTC: maximum 45.8 C, minimum
3164 MiB available RAM, all power readings `0x0`. These are earlier observations,
not measurements of the instant the connection disappeared. On reconnection,
inspect the latest health history and previous-boot journal before another build.
The central audio filter has not been installed on the live server.
