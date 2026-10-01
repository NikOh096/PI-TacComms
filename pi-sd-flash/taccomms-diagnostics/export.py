import json,subprocess
from pathlib import Path
subprocess.run(['python3','/usr/local/lib/taccomms-diagnostics/monitor.py'],capture_output=True,text=True,check=True)
base=Path('/var/lib/taccomms-diagnostics')
samples=[]
for p in (base/'health.previous.jsonl',base/'health.jsonl'):
    if p.exists():
        for line in p.read_text().splitlines():
            try:samples.append(json.loads(line))
            except ValueError:pass
print(json.dumps({'report':json.loads((base/'latest-report.json').read_text()),'recent_health_samples':samples[-120:]},indent=2))
