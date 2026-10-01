from pathlib import Path
import subprocess
import time

def command(*args):
    return subprocess.run(args, capture_output=True, text=True, timeout=15)

server_pid = command('systemctl', 'show', 'mumble-server.service', '-p', 'MainPID', '--value').stdout.strip()
subprocess.run(['systemctl', 'restart', 'halow-console.service'], check=True)
invocation = command('systemctl', 'show', 'halow-console.service', '-p', 'InvocationID', '--value').stdout.strip()
assert len(invocation) == 32
deadline = time.monotonic() + 100
announced = False
suspended = False
while time.monotonic() < deadline:
    logs = command('journalctl', '_SYSTEMD_INVOCATION_ID=' + invocation, '--no-pager', '--output=cat').stdout
    if 'DDC power control detected' in logs and not announced:
        print('Automatic display control enabled. Waiting for the normal one-minute inactivity timeout.', flush=True)
        announced = True
    if 'Display suspended' in logs:
        suspended = True
        break
    time.sleep(2)
if not suspended:
    raise RuntimeError('No automatic suspend observed in 100 seconds; touch may have restarted the timer.\n' + logs)
print(logs.strip(), flush=True)
power = command('ddcutil', '--bus', '20', '--skip-ddc-checks', '--mccs', '2.2', '--disable-dynamic-sleep', '--sleep-multiplier', '2', 'getvcp', 'D6')
print(power.stdout.strip(), power.stderr.strip(), flush=True)
assert power.returncode == 0 and '0x03' in power.stdout, 'Screen did not report suspend state after the timer'
assert command('systemctl', 'show', 'mumble-server.service', '-p', 'MainPID', '--value').stdout.strip() == server_pid
subprocess.run(['systemctl', 'is-active', 'mumble-server.service', 'halow-console.service'], check=True)
print('PASS: automatic 60-second suspend verified; Mumble PID unchanged. Tap the screen to wake.', flush=True)
