import os, subprocess
from pathlib import Path
build=Path('/home/niko/taccomms-noise-build')
build.mkdir(exist_ok=True,mode=0o755)
import pwd
user=pwd.getpwnam('niko')
os.chown(build,user.pw_uid,user.pw_gid)
packages=['cmake','ninja-build','libboost-dev','libcap-dev','libopus-dev',
          'libprotobuf-dev','protobuf-compiler','libssl-dev','libzeroc-ice-dev',
          'zeroc-ice-compilers','qtbase5-dev','libavahi-compat-libdnssd-dev',
          'nlohmann-json3-dev','dpkg-dev','patch']
r=subprocess.run(['apt-get','-s','install','--no-install-recommends','--no-remove',*packages],
                 text=True,capture_output=True,timeout=45)
print(r.stdout)
print(r.stderr)
raise SystemExit(r.returncode)
