import os,signal
from pathlib import Path
base=b'/home/niko/taccomms-noise-build/'
for p in Path('/proc').glob('[0-9]*'):
    try:
        cmd=(p/'cmdline').read_bytes()
        if b'/cc1\x00' not in cmd or base not in cmd or b'rnnoise_data.c' not in cmd:continue
        pid=int(p.name)
        # Follow cc1 -> compiler driver -> Ninja, validating every process.
        def parent(pid):
            return int(next(x.split()[1] for x in Path('/proc',str(pid),'status').read_text().splitlines() if x.startswith('PPid:')))
        ninja=parent(pid)
        for _ in range(5):
            if Path('/proc',str(ninja),'comm').read_text().strip()=='ninja':break
            ninja=parent(ninja)
        nc=Path('/proc',str(ninja),'comm').read_text().strip()
        assert nc=='ninja' and Path('/proc',str(ninja),'cwd').resolve()==Path('/home/niko/taccomms-noise-build/build')
        print('Stopping only isolated model compilation:',pid,'and Ninja',ninja,flush=True)
        os.kill(ninja,signal.SIGKILL);os.kill(pid,signal.SIGTERM)
    except (FileNotFoundError,ProcessLookupError):pass
