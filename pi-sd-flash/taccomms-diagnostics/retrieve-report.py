"""Save a validated report atomically; retain the previous copy on SSH failure."""
import datetime,json,subprocess,sys
from pathlib import Path
base=Path(__file__).resolve().parents[1]
r=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(base/'taccomms-diagnostics/export.py'),'--python','--timeout','90'],capture_output=True,text=True,timeout=100)
if r.returncode:
    print(r.stderr[-2000:]);raise SystemExit(r.returncode)
data=json.loads(r.stdout)
stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
path=base/'private'/('diagnostics-'+stamp+'.json')
path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
print('Saved verified report:',path)
print('Samples:',len(data['recent_health_samples']))
