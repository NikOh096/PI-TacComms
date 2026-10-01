"""PIN-authorized, fixed-path controls for the optional custom Mumble filter."""
import json
import os
from pathlib import Path
import tempfile

CONFIG=Path('/var/lib/taccomms-audio/noise.conf')
INFO=Path('/usr/local/lib/taccomms-noise/build-info.json')

def installed():
    return INFO.is_file()

def status():
    if not installed():
        return ['Central noise filter: not installed.']
    mode=CONFIG.read_text().strip() if CONFIG.exists() else 'off'
    return ['Central noise filter: '+('ON' if mode=='on' else 'OFF'),
            'ON: noise suppression + peak limiter.',
            'Mono Opus: 10/20/40/60 ms packets.',
            'Peak limiting is before Opus encoding.',
            'Experimental; headset/range test pending.']

def set_mode(mode):
    if mode not in ('on','off'):
        raise ValueError('Use noise on or noise off.')
    if not installed():
        raise ValueError('The custom server filter is not installed.')
    fd,name=tempfile.mkstemp(prefix='.taccomms-noise-',dir=CONFIG.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            stream.write(mode+'\n');stream.flush();os.fsync(stream.fileno())
        os.chmod(name,0o644)
        os.replace(name,CONFIG)
    finally:
        Path(name).unlink(missing_ok=True)
    return status()+['Takes effect within one second; calls stay connected.']
