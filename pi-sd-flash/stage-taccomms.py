import hashlib, json, subprocess
from pathlib import Path

base=Path(__file__).resolve().parent
folder=base/'taccomms-admin'
files=sorted(p for p in folder.iterdir() if p.suffix in ('.py','.service'))
manifest={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(folder/'manifest.json').write_text(json.dumps(manifest,indent=2))
args=[r'C:\Windows\System32\OpenSSH\scp.exe','-q','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
      '-o','UserKnownHostsFile='+str(base/'private/known_hosts'),'-i',str(base/'private/halow-pi-ed25519')]
subprocess.run(args+[str(p) for p in files]+[str(folder/'manifest.json'),'niko@10.12.194.1:/home/niko/taccomms-stage/'],check=True)
print('Staged',len(files),'source/unit files with SHA-256 manifest.')
