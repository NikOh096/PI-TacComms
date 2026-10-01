# TacComms — installed on the Pi

Updated 2026-09-29. The secure touchscreen, admin backend and approved software hardening are installed. USB management address: **10.12.194.1**. Reserved Ethernet address: **10.42.0.137**. The Pi recovered without reflashing; both HD01s are now paired and Pixel login as N1K0 is verified.

## Touchscreen

- Tap the main area to cycle Status / Logs / Processes, with the restored cyan TacComms header. The bottom **Admin** button opens the PIN prompt and keyboard.
- Two different six-digit PINs are enrolled on the Pi, with confirmation. No PIN from chat was configured. The Pi has reported successful enrollment.
- The bottom **Lock** button opens a confirmation prompt before emergency locking. This replaces the earlier double/five-tap gestures at the user's request. Cancel returns to the menu; Confirm locks controls.
- Emergency lock persists in protected storage. It clears admin sessions and blocks commands while Mumble keeps running. Only the separate recovery PIN clears it. Admin access still requires its own PIN afterward.
- Admin locks after 60 seconds of inactivity. Failed PIN attempts incur persistent, increasing delays. PINs are stored as salted scrypt hashes.
- Calibration now uses three fitting targets and a fourth accuracy check. It was reopened at the user's request. Final physical shortcut/recovery confirmation remains pending.
- The working 50 kHz HDMI DDC overlay and D6=3 suspend / D6=1 wake are preserved. The new UI has logged automatic suspend; final physical wake confirmation for the new UI remains pending.
- Frontend runs as the unprivileged taccomms account; backend uses a restricted Unix socket and command allowlist. There is no arbitrary root shell in the touchscreen.

## Admin controls

Type `help`, `help users`, `help access`, `help channels`, or `help system`.

Controls include live users/devices with speaker icons; channels; mute/deafen/priority/move/kick; certificate registration, bans, revoke and unban; password set/clear; PIN changes; logs/audit; network/process status; protected backup; service start/stop/restart; reboot/shutdown; calibration and locking.

Speaker indicators use seconds-since-last-voice metadata and can linger for about one second. No audio is captured. Revocation bans the certificate; a new certificate is a new identity, so rotate the shared password if compromised. Sensitive prompts are masked and values are excluded from audit records. Password changes do not update old saved credentials on this PC or phones.

## Approved software hardening

Automatic approval review initially blocked the persistent firewall/service changes because of connectivity and management lockout risk. The user then approved the exact settings. Application passed fresh USB SSH and Mumble TCP/TLS + UDP tests; the rollback timer was cancelled after fresh-session verification.

- Own nftables input table: local Ethernet/USB voice; USB-subnet SSH/DNS management; DHCP, ICMP and mDNS retained. Existing NetworkManager USB-sharing rules preserved.
- Mumble Ice API on **127.0.0.1:6502 only**, protected by a random secret.
- SSH: niko/key-only, no root/password login or X11/agent/TCP forwarding.
- Unused printing, RPC/NFS and remote-desktop services disabled/masked.
- Alternate getty login templates and Ctrl-Alt-Delete target masked; logind configured not to create additional virtual terminals.
- Trusted root/USB SSH access remains. This is local-control protection, **not disk encryption or protection from SD-card removal, root access or power disconnection**.

## Validation and recovery

PIN tests passed: separate PIN enforcement, emergency persistence on reload, UID-bound/expiring sessions, persistent rate limits and invalidated sessions. Current menu tests passed: tap-to-cycle, wake tap without changing pages, Admin PIN prompt, Lock confirmation/cancel, keyboard input, swapped/inverted touch axes and the calibration accuracy check. Earlier gesture tests apply to the superseded gesture UI.

A temporary loopback-only Mumble server passed real TLS/password persistence, channels, mute/deafen/move/priority, certificate registration/ban/unban/revoke, same-IP isolation and emergency command denial. It was removed afterward. Production Mumble still accepts its original saved password and answers UDP from the PC after hardening.

RGB565 packing and screen previews were checked. Unrelated local accounts cannot open the admin socket. Services are active and enabled after the later recovery boot; no reflash was needed.

Installed code: `/opt/taccomms/`. Units: `taccomms-screen.service`, `taccomms-admin.service`, `taccomms-firewall.service`. Protected state/audit: `/var/lib/taccomms/`. Touch calibration: `/var/lib/taccomms-ui/touch.json`.

Backups:
- `/var/lib/halow-setup/backups/before-secure-admin-20260928-223810`
- `/var/lib/halow-setup/backups/before-hardening-20260928-225131`
- `/var/lib/halow-setup/backups/before-taccomms-20260928-220432`

Legacy halow-console remains installed but disabled. An administrator can stop the secure screen and re-enable it for recovery; that restores the old unprotected status-only interface.

## Remaining HaLow/phone work

See PHONE-CONNECTION-GUIDE.md. H7608 is **TC-HTRT01** at 10.42.0.1. Node BFD0 is **TC-HTHD01** at 10.42.0.160; A04E is **TC-HTHD02** at 10.42.0.161. Both bridge their Wi-Fi hotspots to the gateway over HaLow, United States channel 25 / 914.5 MHz / 1 MHz. User-requested Wi-Fi, HaLow and administrator passwords are installed and verified with fresh logins. All three hostnames/radio names and node DHCP reservations are verified. Pixel login through node 2 is verified; a two-phone audio conversation remains to be tested. Protected PC configuration backup: private/tc-network-configured-20260929-005114.tar.gz.

The pending screen service change is installed and systemd reloaded: Wants replaces Requires for the backend. This lets the screen remain available through backend restarts. The current boot logged one screen restart while the backend socket was starting; it then became active with both PINs and calibration intact.

PiSugar S Plus percentage remains unavailable until a gauge is fitted. See battery-sensor/WIRING-GUIDE.md.
