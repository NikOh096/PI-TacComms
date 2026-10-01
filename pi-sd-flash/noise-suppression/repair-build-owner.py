import os,pwd
from pathlib import Path
base=Path('/home/niko/taccomms-noise-build').resolve()
assert str(base)=='/home/niko/taccomms-noise-build' and base.is_dir()
user=pwd.getpwnam('niko')
for path in base.iterdir():
    if path.is_file() and not path.is_symlink():
        os.chown(path,user.pw_uid,user.pw_gid)
print('Top-level build inputs owned by build account.')
