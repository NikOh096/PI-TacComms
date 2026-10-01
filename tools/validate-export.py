"""Offline source/handoff validation. Does not connect to or alter devices."""
import ast
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
paths = sorted(set(p for p in paths if p))
errors = []
counts = {'python': 0, 'json': 0, 'files': len(paths)}
private_parts = {'private', 'card-inventory', 'setup-tools', 'android-tools', 'analysis-tools', 'inspect', 'windows-build', '__pycache__'}
for name in paths:
    path = ROOT / name
    if not path.is_file():
        continue
    if private_parts.intersection(Path(name).parts) or path.name in ('pins.json', 'settings.json', 'credentials.json', 'known_hosts'):
        errors.append(name + ': private/generated file included')
    if path.stat().st_size > 10_000_000:
        errors.append(name + ': unexpected large artifact')
    if path.suffix in ('.dtbo', '.wav'):
        continue
    try:
        text = path.read_text(encoding='utf-8-sig')
    except UnicodeDecodeError:
        errors.append(name + ': unreviewed binary')
        continue
    if any(marker in text for marker in ('-----BEGIN OPENSSH PRIVATE' + ' KEY-----', '-----BEGIN RSA PRIVATE' + ' KEY-----', '-----BEGIN PRIVATE' + ' KEY-----')):
        errors.append(name + ': private-key marker')
    try:
        if path.suffix == '.py':
            ast.parse(text, filename=name)
            counts['python'] += 1
        elif path.suffix == '.json':
            json.loads(text)
            counts['json'] += 1
    except (SyntaxError, ValueError) as exc:
        errors.append(name + ': ' + str(exc))

handoff = json.loads((ROOT / 'codex-handoff.json').read_text())
for name in handoff['read_first'] + handoff['noise_filter']['entry_points']:
    if not (ROOT / name).is_file():
        errors.append('Missing handoff reference: ' + name)
if handoff['code_state']['noise_deployed'] is not False:
    errors.append('Handoff incorrectly claims noise deployment')
if handoff['network']['phone_settings']['mobile_data'] is not True:
    errors.append('Handoff must preserve mobile data')
print(json.dumps({'passed': not errors, 'counts': counts, 'errors': errors}, indent=2))
raise SystemExit(bool(errors))
