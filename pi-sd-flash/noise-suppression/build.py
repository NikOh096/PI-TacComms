"""Build as niko, separately from the installed server. Never deploy here."""
import hashlib,os,subprocess,tarfile
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build')
os.chdir(base)
assert os.geteuid()!=0,'Compile as the unprivileged build account.'
source=base/'mumble-1.5.735'
marker=base/'debian-patches-applied'
if not marker.exists():
    assert not source.exists(),'Review partial source directory before continuing.'
    for name,digest in [('mumble_1.5.735.orig.tar.gz','db8990079f556a877218d471bcf2c24eb5e4520b652f3c20793d0aadedaae6ae'),('mumble_1.5.735-5+deb13u1.debian.tar.xz','4f62bb77c7e4c645549aba463f39bfda57eaf303ca70f2c8d5bc08d8585d1bca')]:
        path=base/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
        with tarfile.open(path) as archive:
            archive.extractall(base if '.orig.' in name else source,filter='data')
    for name in (source/'debian/patches/series').read_text().splitlines():
        if name.strip() and not name.lstrip().startswith('#'):
            subprocess.run(['patch','-p1','--forward','--batch','-i',str(source/'debian/patches'/name.strip())],cwd=source,check=True)
    marker.write_text('1.5.735-5+deb13u1\n')
subprocess.run(['python3',str(base/'patch-source.py'),str(source)],check=True)
flags='-O2 -fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE'
subprocess.run(['cmake','-S',str(source),'-B',str(base/'build'),'-G','Ninja',
    '-Dclient=OFF','-Dserver=ON','-Dice=ON','-Dplugins=OFF','-Doverlay=OFF',
    '-Dtests=OFF','-Dlto=OFF','-Dwarnings-as-errors=OFF','-DBUILD_NUMBER=735',
    '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_FLAGS='+flags,'-DCMAKE_CXX_FLAGS='+flags,
    '-DCMAKE_EXE_LINKER_FLAGS=-Wl,-z,relro,-z,now -pie'],check=True)
subprocess.run(['cmake','--build',str(base/'build'),'--parallel','1'],check=True)
print('ISOLATED BUILD COMPLETE; installed Mumble is unchanged.',flush=True)
