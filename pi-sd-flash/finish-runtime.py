"""Apply small runtime corrections and update the local clock from this PC."""
from pathlib import Path
import subprocess
import sys
import time

base = Path(__file__).resolve().parent
remote = base / 'finish-runtime-remote.py'
remote.write_text('''from pathlib import Path
import subprocess
subprocess.run(['date', '-u', '-s', '@%d'], check=True, stdout=subprocess.DEVNULL)
Path('/var/lib/systemd/timesync').mkdir(parents=True, exist_ok=True)
Path('/var/lib/systemd/timesync/clock').touch()
Path('/etc/sysctl.d/90-halow-console.conf').write_text('# Keep messages in the journal; live power status is shown on the console.\\nkernel.printk = 1 4 1 3\\n')
subprocess.run(['sysctl', '-p', '/etc/sysctl.d/90-halow-console.conf'], check=True)
subprocess.run(['systemctl', 'restart', 'halow-console.service'], check=True)
subprocess.run(['systemctl', 'is-active', 'mumble-server.service'], check=True)
subprocess.run(['vcgencmd', 'get_throttled'], check=True)
print('Updated the clock and console; kernel logs remain available in the journal.')
''' % int(time.time()), encoding='utf-8')
sys.exit(subprocess.run([sys.executable, str(base/'pi-admin.py'), str(remote), '--python']).returncode)
