from pathlib import Path
import subprocess
import time

subprocess.run(['systemctl', 'restart', 'halow-console.service'], check=True)
deadline = time.monotonic() + 25
while time.monotonic() < deadline:
    screen = Path('/dev/vcs1').read_bytes().decode('ascii', errors='replace')
    if 'Battery %: unsupported (S Plus)' in screen and 'PiSugar input:' in screen:
        print('Verified live console: battery percentage unsupported; external input labeled separately.')
        break
    time.sleep(1)
else:
    raise RuntimeError('Updated labels did not appear on the live console')
subprocess.run(['systemctl', 'is-active', 'mumble-server.service', 'halow-console.service'], check=True)
subprocess.run(['vcgencmd', 'get_throttled'], check=True)
