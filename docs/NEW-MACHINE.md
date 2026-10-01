# Continue on another machine

## 1. Obtain source and private access separately

Clone `https://github.com/NikOh096/PI-TacComms.git`. Open the repository in Codex
and tell it to read `codex-handoff.json` and `AGENTS.md` before continuing.

Using an encrypted transfer, copy these files from the original workstation into
the same relative paths in the new checkout:

| File | Purpose |
| --- | --- |
| `pi-sd-flash/private/credentials.json` | Existing Pi sudo and Mumble credentials |
| `pi-sd-flash/private/halow-pi-ed25519` | Existing authorized SSH private key |
| `pi-sd-flash/private/known_hosts` | Pinned identity of the actual Pi |
| `pi-sd-flash/private/tc-network.json` | Existing Heltec password/node mapping |
| Existing private recovery backups, if needed | Device state and recovery, not source |

Do not upload these files or paste their contents into issues. Restrict access to
your account (on Linux/macOS, directory mode 700 and private files mode 600).
Examples under `pi-sd-flash/examples/` document field names only. They are not
working credentials. Do not run `generate-credentials.py` for the existing Pi.

To use a new SSH key instead, add its public key through an existing trusted
management connection. Keep the old access until a new connection succeeds.
Never solve a changed-host-key error by disabling strict host checking.

## 2. Install tools

Use Python 3.12+ and OpenSSH. `pi-admin.py` now finds SSH on PATH; optionally set
`TACCOMMS_SSH` to the executable. Windows-specific historical scripts still need
review on another OS. Local PIN/diagnostics tests use the Python standard library.
The Pi frontend uses Pillow, evdev and installed DejaVu fonts; the backend uses
the distribution's ZeroC Ice bindings. Do not replace those with arbitrary
packages while importing the repository.

If phone debugging is needed, install Android SDK Platform Tools and authorize
the new machine on the unlocked phone. Set `ANDROID_SERIAL` from `adb devices -l`;
the old phone's serial is not published. Optionally set `TACCOMMS_ADB`, otherwise
the helpers use `adb` on PATH or the original ignored local tools location.
ADB and developer mode are unnecessary for normal Mumla calls.

## 3. Connect and inspect before modifying

Keep stable Pi power and the Pi-to-gateway Ethernet cable. Connect a known-good
USB-C data cable directly to the computer. The Pi management address is
10.12.194.1; SSH user is niko. Ethernet SSH is intentionally blocked.

From repository root, this read-only check uses the trusted pin and key:

```sh
ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=yes -o UserKnownHostsFile=pi-sd-flash/private/known_hosts -i pi-sd-flash/private/halow-pi-ed25519 niko@10.12.194.1 "uptime; cat /proc/sys/kernel/random/boot_id; vcgencmd get_throttled; systemctl is-active mumble-server taccomms-admin taccomms-screen taccomms-diagnostics"
```

Inspect current live files and root-only diagnostics through the existing
authorized administration path. `pi-admin.py SCRIPT --python` sends a reviewed
Python script with sudo credentials through SSH stdin; `--user` runs it as niko.
It executes the script you provide: read it before using it. Do not run historical
recovery, firewall, clock, calibration, or installation scripts as a smoke test.

## 4. Preserve state and continue narrowly

On the Pi, protect `/var/lib/taccomms/` (PIN state/audit),
`/var/lib/taccomms-ui/touch.json` (calibration), `/etc/mumble/`, and
`/var/lib/mumble-server/` (database/certificate state). Back up before deployment.
The repository does not replace those directories.

Use `health`, `crashlog`, and `help system` in the touchscreen Admin console.
Read `docs/CURRENT-STATE.md` before interpreting older logs or resuming the audio
prototype. The stock Debian Mumble binary remains the rollback target.

For another phone, follow `docs/PHONE-CHECKLIST.md`. Keep mobile data enabled.
