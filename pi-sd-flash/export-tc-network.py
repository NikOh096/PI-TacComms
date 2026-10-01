import base64,io,tarfile
from pathlib import Path
buffer=io.BytesIO()
with tarfile.open(fileobj=buffer,mode='w:gz') as archive:
    folder=Path('/var/lib/taccomms/router-backups')
    for name in ('TC-HTRT01','TC-HTHD01','TC-HTHD02'):
        source=sorted(folder.glob('configured-'+name+'-*.json'))[-1]
        archive.add(source,arcname=name+'.json')
    for filename in ('tc-gateway.json','tc-hthd01.json','tc-hthd02.json'):
        archive.add(Path('/var/lib/taccomms')/filename,arcname=filename)
print(base64.b64encode(buffer.getvalue()).decode())
