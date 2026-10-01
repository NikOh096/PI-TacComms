# TacComms admin — implemented; latest UI uses visible menu buttons

Latest user change: restore tap-to-cycle Status / Logs / Processes with the cyan
TacComms header. Add Admin and Lock buttons. Admin requires the saved admin PIN;
Lock asks for confirmation and uses the separate recovery PIN to unlock. This
supersedes double-tap admin and the five-tap emergency shortcut described in the
earlier requirements below. See ../TACCOMMS-UPDATE.md for installed/verified state.

User requirements (2026-09-28):
- Automatic Mumble startup remains unattended.
- Double tap dashboard to enter a protected admin console with on-screen keyboard.
- First-use enrollment ON THE PI, six digits plus confirmation. Do not hard-code the PIN previously typed in chat.
- Two DIFFERENT six-digit PINs: normal admin and emergency recovery.
- Five complete taps within HALF A SECOND (500 ms) activate emergency lock (latest user instruction). In admin/keyboard views use the header gesture area to prevent ordinary typing from activating it.
- Emergency lock persists over reboot; Mumble calls continue. Recovery requires the separate recovery PIN; admin PIN cannot clear emergency lock.
- Local PIN protection chosen; full-disk encryption was explicitly not selected.
- Admin commands and `help`: status, users/devices (username and activity speaker icon), channels, password set/remove, kick, ban/unban, register/revoke certificate identity, mute/deafen/move, logs/audit, backups, service control and safe power controls.

Security approach:
- Strict command interpreter, no arbitrary shell from the touchscreen.
- Privileged backend over a permission-restricted Unix socket, Ice bound ONLY to loopback with a random secret.
- Salted scrypt PIN hashes, no plaintext PIN storage/logging; persistent failure rate limits; short inactive session lifetime; session invalidation on lock/emergency.
- Explicit in-app confirmation for disruptive/destructive commands.
- Preserve management SSH key access and USB DHCP/DNS while restricting management to USB and voice traffic to local interfaces.
- Preserve NetworkManager's existing nm-shared-usb0 nftables table.
- Remove unnecessary exposed services (currently rpcbind on port 111, printer services), after backup.
- Existing display controller must retain D6=3 suspend / D6=1 wake, 50kHz DDC overlay, and 60-second timeout.

Hardware/API facts:
- Pi framebuffer: /dev/fb0, 640x480, 16bpp, stride1280. Pillow installed; DejaVuSansMono fonts available.
- ADS7846 absX min240/max3900; absY min3900/max240. Calibrate positions physically before declaring on-screen keyboard ready.
- Mumble 1.5.735, installed /usr/share/mumble-server/MumbleServer.ice (module MumbleServer).
- Ice User includes idlesecs: seconds since user last spoke; other activity is not counted. Use this for a short-decay speaking indicator; no audio recording or listening client needed.
- Ice bindings missing; libzeroc-ice3.7t64 3.7.10-3.1 already installed. Fetch python3-zeroc-ice and libmcpp0, verify hashes and apt simulation before installation.
- SSH already disables password auth, keyboard-interactive auth and root login. X11/agent forwarding are still enabled.

Existing TacComms cleanup is installed on all 3 Pi copies and validated live. Original backup:
/var/lib/halow-setup/backups/before-taccomms-20260928-220432
Mumble PID970 was unchanged through that update. First automatic60s suspend passed; second test timed out because screen activity restarted timer. Final current console code adds process filtering to keep Mumble at top and omit ps sampler.

Remaining HaLow/phone work: HT-H7608 V2 firmware2.8.5, hostname WHL-AP-72AA, default root/heltec.org login accepted via /ubus. HaLow radio1 (type=morse) is DISABLED. Both radio interfaces assigned to LAN br-lan10.42.0.1/24 (Ethernet eth0.1), DHCP100-249. This is the confirmed main connection issue; no router changes made yet. Pixel10Pro remains connected via authorized ADB while Pi USB is also connected. Phone currently on HD01-BFD0 WiFi10.42.0.151; mobile data restored. Mumla TacComms/N1K0/10.42.0.137:64738 saved with password; PTT selected but persisted setting and actual connection not yet verified.
