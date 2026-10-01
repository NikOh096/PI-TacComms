# TacComms continuation instructions

Read `codex-handoff.json`, `docs/CURRENT-STATE.md`, and `docs/NEW-MACHINE.md` first.
Those files resolve known contradictions in older dated setup notes.

- Keep the user's phone mobile data enabled. Do not disable it for HaLow tests.
- Keep production voice service and automatic startup working. A failed SSH/USB
  connection alone is not evidence of a Pi crash; compare boot ID and uptime.
- Local `taccomms-admin/backend.py` contains experimental noise commands not
  installed on the Pi. Inspect and compare live files before deployment.
- Central filtering is uninstalled. Its Windows synthetic tests are not Pi
  performance tests or proof of headset intelligibility during real impulses.
- Preserve admin/recovery PINs and touchscreen calibration. The current UI uses
  visible Admin and Lock buttons; old double/five-tap gestures are superseded.
- Display sleep must use the verified DDC suspend/wake, not HDMI signal removal
  or a black framebuffer with the backlight still lit.
- Do not commit private data. Keep SSH keys, passwords, PIN hashes, device
  exports, logs, databases, and recovery images in ignored private storage.
- SSH is pinned, key-only, USB-only. Never disable host checking or bypass the
  management firewall. Transfer credentials privately for another machine.
- Review individual scripts before running them. Historical tools may stage
  one-time boot actions, rotate passwords, restart services, or target a specific
  disk, drive letter, node identity, or clock timestamp. Cloning is not permission
  to execute all scripts. In particular, `sync-clock.py` contains an old timestamp.
- Before changing the working installation, make a protected local backup and
  verify the rollback path. The user already authorized the existing hardening;
  do not repeat approval questions merely to inspect it or preserve it.
- Test local changes with the relevant existing tests. Use one compile worker
  for the unfinished Pi audio build and inspect power diagnostics first.
- Do not claim a MAX17048 gauge was physically installed. Only a proposal and
  reader exist. The owner handles hardware changes.
