import subprocess
from pathlib import Path
for path in ('/proc/uptime','/proc/sys/kernel/random/boot_id'):
    print(path,Path(path).read_text().strip())
for args in [ ['vcgencmd','get_throttled'], ['systemctl','show','mumble-server.service','-p','MainPID','-p','ActiveState'],
              ['ps','-eo','pid,ppid,pcpu,comm','--sort=-pcpu'] ]:
    print(subprocess.run(args,capture_output=True,text=True).stdout[:1600])
print('Denoiser test binary exists:',Path('/home/niko/taccomms-noise-build/build/src/murmur/taccomms-filter-test').exists())
