"""Run a reviewed script on this Pi using its pinned SSH key; keep credentials out of argv/logs."""
import argparse
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser()
parser.add_argument('script', type=Path)
parser.add_argument('--python', action='store_true')
parser.add_argument('--user', action='store_true')
parser.add_argument('--timeout', type=int, default=120)
options = parser.parse_args()
script = options.script.read_text(encoding='utf-8')
interpreter = '/usr/bin/python3 -' if options.python else '/bin/bash -s'
command = interpreter if options.user else "sudo -k -S -p '' -- " + interpreter
payload = script if options.user else json.loads((BASE / 'private/credentials.json').read_text())['pi_password'] + '\n' + script
ssh = os.environ.get('TACCOMMS_SSH') or shutil.which('ssh')
if not ssh:
    raise SystemExit('Install OpenSSH or set TACCOMMS_SSH to its executable.')
args = [ssh, '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=8',
        '-o', 'StrictHostKeyChecking=yes', '-o', 'UserKnownHostsFile=' + str(BASE / 'private/known_hosts'),
        '-i', str(BASE / 'private/halow-pi-ed25519'), 'niko@10.12.194.1', command]
result = subprocess.run(args, input=payload.encode('utf-8'), timeout=options.timeout)
sys.exit(result.returncode)
