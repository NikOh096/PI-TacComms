#!/usr/bin/python3
"""Offline, one-time setup for Niko's Raspberry Pi; never logs credentials."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import time
import traceback

BOOT = Path('/boot/firmware/halow-setup')
STATE = Path('/var/lib/halow-setup')
SOURCE = Path(__file__).resolve().parent
ENV = dict(os.environ, DEBIAN_FRONTEND= 'noninteractive', LC_ALL='C')


def write(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.halow-new')
    temporary.write_text(content, encoding='utf-8')
    temporary.chmod(mode)
    temporary.replace(path)


def run(args, *, secret=False, input=None, check=True, timeout=600):
    if not secret:
        print('Running:', ' '.join(map(str, args)), flush=True)
    result = subprocess.run(list(map(str, args)), input=input, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            env=ENV, timeout=timeout)
    if not secret and result.stdout:
        print(result.stdout, flush=True)
    if check and result.returncode:
        # Deliberately omit argv and output for calls containing credentials.
        raise RuntimeError('Command failed: ' + ('credential operation' if secret else str(args[0])))
    return result


def verify_bundle():
    for line in (SOURCE / 'BUNDLE-SHA256SUMS').read_text().splitlines():
        digest, relative = line.split('  ', 1)
        path = (SOURCE / relative).resolve()
        if not path.is_relative_to(SOURCE) or not path.is_file():
            raise RuntimeError('Invalid bundle path')
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise RuntimeError('Bundle checksum mismatch: ' + relative)
    print('Bundle checksums verified.', flush=True)


def disarm():
    path = Path('/boot/firmware/cmdline.txt')
    tokens = path.read_text().strip().split()
    if 'root=PARTUUID=ff57595b-02' not in tokens:
        raise RuntimeError('Unexpected SD card identity')
    owned = {
        'systemd.run=/boot/firmware/halow-setup/bootstrap.sh',
        'systemd.run_success_action=reboot',
        'systemd.run_failure_action=reboot',
        'systemd.unit=kernel-command-line.target',
    }
    write(path, ' '.join(token for token in tokens if token not in owned) + '\n')
    os.sync()
    print('One-time boot command removed; next boot will be normal.', flush=True)


def bootstrap(settings):
    if run(['dpkg', '--print-architecture']).stdout.strip() != 'arm64':
        raise RuntimeError('This bundle requires arm64 Raspberry Pi OS')
    if 'Raspberry Pi 4 Model B' not in Path('/proc/device-tree/model').read_text():
        raise RuntimeError('Unexpected Pi model')
    user = settings['username']
    if user != 'niko' or settings['hostname'] != 'halow-pi':
        raise RuntimeError('Unexpected setup identity')

    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.chmod(0o700)
    shutil.copytree(SOURCE, STATE, dirs_exist_ok=True)
    (STATE / 'settings.json').chmod(0o600)
    write('/etc/cloud/cloud-init.disabled', '# Configured locally for the dedicated HaLow appliance.\n')
    run(['/usr/lib/userconf-pi/userconf', user, settings['password_hash']], secret=True)
    account = pwd.getpwnam(user)
    if account.pw_uid != 1000 or account.pw_shell != '/bin/bash':
        raise RuntimeError('Login account verification failed')
    home = Path(account.pw_dir)
    ssh = home / '.ssh'
    ssh.mkdir(mode=0o700, exist_ok=True)
    ssh.chmod(0o700)
    os.chown(ssh, account.pw_uid, account.pw_gid)
    keyfile = ssh / 'authorized_keys'
    existing = keyfile.read_text() if keyfile.exists() else ''
    public = settings['ssh_public_key'].strip()
    if not public.startswith('ssh-ed25519 '):
        raise RuntimeError('Invalid SSH public key')
    if public not in existing.splitlines():
        write(keyfile, existing.rstrip() + '\n' + public + '\n', 0o600)
    os.chown(keyfile, account.pw_uid, account.pw_gid)
    write('/etc/ssh/sshd_config.d/00-halow-access.conf',
          'PubkeyAuthentication yes\nPasswordAuthentication no\n'
          'KbdInteractiveAuthentication no\nPermitRootLogin no\n')
    run(['ssh-keygen', '-A'])
    Path('/run/sshd').mkdir(mode=0o755, exist_ok=True)
    run(['/usr/sbin/sshd', '-t'])
    run(['systemctl', 'enable', 'ssh.service'])
    write('/etc/hostname', 'halow-pi\n')
    hosts = Path('/etc/hosts').read_text()
    if re.search(r'^127\.0\.1\.1\s', hosts, re.M):
        hosts = re.sub(r'^127\.0\.1\.1\s.*$', '127.0.1.1\thalow-pi', hosts, flags=re.M)
    else:
        hosts += '\n127.0.1.1\thalow-pi\n'
    write('/etc/hosts', hosts)
    write('/etc/NetworkManager/system-connections/halow-ethernet.nmconnection',
          '[connection]\nid=HaLow Ethernet\nuuid=3b9b8052-969e-48d5-8de1-3dac4a074141\n'
          'type=ethernet\ninterface-name=eth0\nautoconnect=true\nautoconnect-priority=50\n'
          '\n[ethernet]\n\n[ipv4]\nmethod=auto\nroute-metric=100\n'
          '\n[ipv6]\nmethod=auto\n', 0o600)
    write('/etc/modules-load.d/usb-gadget.conf', 'g_ether\n')
    # Dedicated console appliance: the status service owns tty1, with no desktop session.
    old_sudo_user = ENV.get('SUDO_USER')
    ENV['SUDO_USER'] = user
    run(['raspi-config', 'nonint', 'do_boot_behaviour', 'B1'])
    if old_sudo_user is None:
        ENV.pop('SUDO_USER', None)
    else:
        ENV['SUDO_USER'] = old_sudo_user
    run(['raspi-config', 'nonint', 'do_change_timezone', 'America/New_York'])
    write('/etc/default/console-setup', 'ACTIVE_CONSOLES="/dev/tty[1-6]"\n'
          'CHARMAP="UTF-8"\nCODESET="Lat15"\nFONTFACE="TerminusBold"\nFONTSIZE="32x16"\n')
    write('/etc/modules-load.d/halow-display.conf', 'i2c-dev\n')
    write('/etc/sysctl.d/90-halow-console.conf',
          '# Keep kernel messages in the journal; show supply status on the console.\nkernel.printk = 1 4 1 3\n')
    write('/usr/local/bin/halow-console', (SOURCE / 'console.py').read_text(), 0o755)
    write('/etc/systemd/system/halow-console.service', '''[Unit]
Description=HaLow touchscreen status console
After=systemd-user-sessions.service console-setup.service NetworkManager.service
Conflicts=getty@tty1.service

[Service]
Type=simple
ExecStartPre=-/usr/bin/setfont -C /dev/tty1 /usr/share/consolefonts/Lat15-TerminusBold32x16.psf.gz
ExecStartPre=-/usr/bin/chvt 1
ExecStart=/usr/local/bin/halow-console
Restart=always
RestartSec=3
StandardInput=tty
StandardOutput=tty
StandardError=journal
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Environment=TERM=linux

[Install]
WantedBy=multi-user.target
''')
    run(['systemctl', 'mask', 'getty@tty1.service'])
    run(['systemctl', 'enable', 'halow-console.service'])
    write('/etc/systemd/system/halow-provision.service', '''[Unit]
Description=Finish offline HaLow voice setup
After=NetworkManager.service
Wants=NetworkManager.service
ConditionPathExists=/var/lib/halow-setup/settings.json

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /var/lib/halow-setup/setup.py provision
TimeoutStartSec=15min

[Install]
WantedBy=multi-user.target
''')
    run(['systemctl', 'enable', 'halow-provision.service'])
    print('Bootstrap complete. Normal boot will install and start Mumble.', flush=True)


def install_packages():
    metadata = json.loads((SOURCE / 'packages.json').read_text())
    packages = [SOURCE / 'debs' / item['filename'] for item in metadata]
    for item, path in zip(metadata, packages):
        if path.stat().st_size != item['size'] or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
            raise RuntimeError('Debian package checksum mismatch: ' + item['name'])
    # APT --no-download also skips acquisition of local .deb files on this release.
    # Resolve dependencies without making changes, then install the verified files with dpkg.
    simulation = run(['apt-get', '--simulate', '--no-remove', '--no-install-recommends',
                      'install', *packages]).stdout
    planned = set(re.findall(r'^Inst (\S+)', simulation, re.M))
    if not planned.issubset({item['name'] for item in metadata}) or re.search(r'^Remv ', simulation, re.M):
        raise RuntimeError('APT requires packages outside the verified offline bundle')
    policy = Path('/usr/sbin/policy-rc.d')
    saved = Path('/usr/sbin/policy-rc.d.halow-original')
    if saved.exists():
        raise RuntimeError('An earlier service-start policy backup needs inspection')
    had_policy = policy.exists() or policy.is_symlink()
    if had_policy:
        policy.rename(saved)
    try:
        write(policy, '#!/bin/sh\nexit 101\n', 0o755)
        run(['dpkg', '--install', *packages], timeout=720)
    finally:
        policy.unlink(missing_ok=True)
        if had_policy:
            saved.rename(policy)
    if run(['dpkg', '--audit']).stdout.strip():
        raise RuntimeError('dpkg reported an incomplete package installation')
    for item in metadata:
        actual = run(['dpkg-query', '-W', '-f=${Status}|${Version}', item['name']]).stdout
        if actual != 'install ok installed|' + item['version']:
            raise RuntimeError('Installed package verification failed: ' + item['name'])


def provision(settings):
    # Networking management remains available even if the package install later fails.
    run(['rpi-usb-gadget', 'on'], timeout=90)
    if not Path('/etc/modules-load.d/usb-gadget.conf').exists():
        raise RuntimeError('USB management could not be configured')
    install_packages()
    run(['systemctl', 'stop', 'mumble-server.service'], check=False)
    config = Path('/etc/mumble/mumble-server.ini')
    backup = STATE / 'mumble-server-original.ini'
    if not backup.exists():
        shutil.copy2(config, backup)
    write(config, '''# HaLow local voice server
database=/var/lib/mumble-server/mumble-server.sqlite
logfile=
host=0.0.0.0
port=64738
serverpassword={password}
bandwidth=64000
users=100
registerName=HaLow Voice
registerPassword=
bonjour=true
allowhtml=false
opusthreshold=0
allowping=true
ice=
welcometext=Welcome to HaLow Voice. Use push-to-talk and 24 kbit/s Opus on the radio network.
'''.format(password=settings['mumble_password']), 0o640)
    shutil.chown(config, user='root', group='mumble-server')
    run(['runuser', '-u', 'mumble-server', '--', '/usr/bin/mumble-server',
         '-ini', config, '-readsupw'], input=settings['admin_password'] + '\n', secret=True)
    write('/usr/local/bin/halow-status', (SOURCE / 'status.py').read_text(), 0o755)
    write('/etc/systemd/system/halow-status.service', '''[Unit]
Description=Record HaLow voice and touchscreen status
After=NetworkManager.service mumble-server.service halow-provision.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/halow-status --save
TimeoutStartSec=45

[Install]
WantedBy=multi-user.target
''')
    run(['systemctl', 'daemon-reload'])
    run(['systemctl', 'enable', '--now', 'mumble-server.service'])
    run(['systemctl', 'enable', 'halow-status.service'])
    run(['systemctl', 'is-active', '--quiet', 'mumble-server.service'])
    # Ensure both transports are listening before declaring setup successful.
    for attempt in range(20):
        tcp = run(['ss', '-H', '-lnt', 'sport = :64738']).stdout.strip()
        udp = run(['ss', '-H', '-lnu', 'sport = :64738']).stdout.strip()
        if tcp and udp:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Mumble did not open both TCP and UDP port 64738')
    write(STATE / 'complete.json', json.dumps({'status': 'installed', 'username': settings['username'],
                                             'hostname': settings['hostname'], 'time': time.time()}, indent=2) + '\n')
    for temporary_secret in [BOOT / 'settings.json', STATE / 'settings.json']:
        temporary_secret.unlink(missing_ok=True)
    run(['/usr/local/bin/halow-status', '--save'])
    print('Mumble installed and listening on TCP/UDP 64738. Phone/radio call test remains.', flush=True)


def main():
    if os.geteuid() != 0:
        raise SystemExit('Run as root')
    phase = sys.argv[1]
    if phase not in ('bootstrap', 'provision'):
        raise SystemExit('Unknown phase')
    # Disarm before any setup work, so even a failed package install cannot create a boot loop.
    if phase == 'bootstrap':
        disarm()
    log = open(BOOT / (phase + '.log'), 'a', buffering=1)
    os.dup2(log.fileno(), 1)
    os.dup2(log.fileno(), 2)
    print(time.strftime('%Y-%m-%d %H:%M:%S'), phase, 'started', flush=True)
    try:
        verify_bundle()
        settings = json.loads((SOURCE / 'settings.json').read_text())
        if phase == 'bootstrap':
            bootstrap(settings)
        else:
            provision(settings)
    except Exception:
        traceback.print_exc()
        write(BOOT / 'setup-state.txt', phase.upper() + ' FAILED; inspect ' + phase + '.log\n')
        raise SystemExit(1)
    else:
        write(BOOT / 'setup-state.txt', phase.upper() + ' COMPLETE\n')
    finally:
        os.sync()


if __name__ == '__main__':
    main()
