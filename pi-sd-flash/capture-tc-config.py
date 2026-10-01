import base64,datetime,hashlib,io,json,subprocess,sys,tarfile
from pathlib import Path
base=Path(__file__).resolve().parent
result=subprocess.run([sys.executable,str(base/'pi-admin.py'),str(base/'export-tc-network.py'),'--python'],capture_output=True,check=True)
data=base64.b64decode(result.stdout.strip(),validate=True)
with tarfile.open(fileobj=io.BytesIO(data),mode='r:gz') as archive:
    for item in archive:
        if item.isfile():json.loads(archive.extractfile(item).read())
target=base/'private'/('tc-network-configured-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.tar.gz')
target.write_bytes(data)
assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(data).digest()
print('Verified network configuration backup:',target.name)
