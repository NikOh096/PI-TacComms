"""Supply user-requested router credentials through SSH stdin, without logging them."""
import json, subprocess, sys
from pathlib import Path
base=Path(__file__).resolve().parent
settings=json.loads((base/'private/tc-network.json').read_text())
source=Path(sys.argv[1])
payload='PASSWORD='+repr(settings['password'])+'\n'+(base/'tc-router-common.py').read_text()+'\n'+source.read_text()
temporary=base/'private/tc-remote-current.py'
temporary.write_text(payload,encoding='utf-8')
try:
    result=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(temporary),'--python','--timeout','160'])
finally:temporary.unlink(missing_ok=True)
raise SystemExit(result.returncode)
