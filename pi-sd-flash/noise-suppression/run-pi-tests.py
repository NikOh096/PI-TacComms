import hashlib,json,subprocess
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build')
exe=base/'build/src/murmur/taccomms-filter-test'
digest=hashlib.sha256(exe.read_bytes()).hexdigest()
for name,args in [('core',[]),('load',['--load'])]:
    r=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=120)
    print(r.stdout,end='',flush=True)
    if r.stderr:print(r.stderr,end='',flush=True)
    assert r.returncode==0,name+' test failed'
    result=json.loads(r.stdout);assert result['passed']
    result['test_binary_sha256']=digest
    (base/('pi-'+name+'-result.json')).write_text(json.dumps(result,indent=2)+'\n')
assert hashlib.sha256(exe.read_bytes()).hexdigest()==digest,'Test binary changed during test.'
subprocess.run(['python3',str(base/'test-integration.py')],check=True,timeout=100)
