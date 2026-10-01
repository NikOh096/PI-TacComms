import datetime,json,os,shutil,subprocess
from pathlib import Path
def run(*args,check=True):
    return subprocess.run(args,text=True,capture_output=True,check=check).stdout.strip()
backup=Path('/var/lib/halow-setup/backups')/('before-hardening-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(mode=0o700,parents=True)
(backup/'nft.txt').write_text(run('nft','list','ruleset'))
(backup/'sshd.txt').write_text(run('sshd','-T'))
(backup/'enabled-units.txt').write_text(run('systemctl','list-unit-files','--state=enabled','--no-pager'))
for p in backup.iterdir():p.chmod(0o600)
private=Path('/etc/taccomms'); private.mkdir(mode=0o700,exist_ok=True)
firewall=private/'firewall.nft'
firewall.write_text('''destroy table inet taccomms
table inet taccomms {
 chain input {
  type filter hook input priority 0; policy drop;
  iifname "lo" accept
  ct state established,related accept
  ct state invalid drop
  ip protocol icmp accept
  meta l4proto ipv6-icmp accept
  iifname "eth0" udp sport 67 udp dport 68 accept
  iifname "usb0" udp sport 68 udp dport 67 accept
  iifname "usb0" ip saddr 10.12.194.0/28 tcp dport { 22, 53 } accept
  iifname "usb0" ip saddr 10.12.194.0/28 udp dport 53 accept
  iifname { "eth0", "usb0" } tcp dport 64738 accept
  iifname { "eth0", "usb0" } udp dport 64738 accept
  iifname { "eth0", "usb0" } udp dport 5353 accept
 }
}
''')
run('nft','--check','--file',str(firewall))
unit=Path('/etc/systemd/system/taccomms-firewall.service')
unit.write_text('''[Unit]
Description=TacComms local voice and USB management firewall
Before=taccomms-admin.service
After=network-pre.target
Wants=network-pre.target
[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/usr/sbin/nft -f /etc/taccomms/firewall.nft
ExecReload=/usr/sbin/nft -f /etc/taccomms/firewall.nft
ExecStop=-/usr/sbin/nft delete table inet taccomms
[Install]
WantedBy=multi-user.target
''')
run('systemctl','daemon-reload')
run('systemd-run','--unit=taccomms-firewall-rollback','--on-active=180s','/usr/bin/systemctl','disable','--now','taccomms-firewall.service')
run('systemctl','enable','--now','taccomms-firewall.service')
ssh=Path('/etc/ssh/sshd_config.d/00-taccomms.conf')
assert not ssh.exists(), 'Existing hardening config needs review'
ssh.write_text('''# USB management is enforced by the TacComms firewall.
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
AllowUsers niko
X11Forwarding no
AllowAgentForwarding no
AllowTcpForwarding no
PermitTunnel no
MaxAuthTries 3
LoginGraceTime 30
''')
run('sshd','-t'); run('systemctl','reload','ssh.service')
# Prevent device-triggered activation of services the voice appliance does not use.
services=['cups.path','cups.service','cups.socket','rpcbind.service','rpcbind.socket',
          'nfs-client.target','nfs-blkmap.service','wayvnc-control.service','lightdm.service']
for name in services:
    run('systemctl','disable','--now',name,check=False)
    run('systemctl','mask',name,check=False)
# Physical keyboards must not open an alternate login or trigger Ctrl-Alt-Delete.
for name in ['getty@.service','serial-getty@.service','ctrl-alt-del.target']:
    run('systemctl','mask',name)
for number in range(1,7):run('systemctl','stop',f'getty@tty{number}.service',check=False)
drop=Path('/etc/systemd/logind.conf.d'); drop.mkdir(exist_ok=True)
(drop/'taccomms.conf').write_text('[Login]\nNAutoVTs=0\nReserveVT=0\n')
print('Backup:',backup)
print('Firewall applied; automatic rollback armed for three minutes.')
print('Verify a NEW SSH connection, then cancel taccomms-firewall-rollback.timer.')
print('Mumble:',run('systemctl','is-active','mumble-server.service'))
