"""Task-scoped Android setup helpers; never print saved credentials."""
import json
import os
import shutil
from pathlib import Path
import re
import shlex
import subprocess
import sys
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')

BASE = Path(__file__).resolve().parent
ADB = os.environ.get('TACCOMMS_ADB') or shutil.which('adb') or str(BASE / 'android-tools/platform-tools/adb.exe')
SERIAL = os.environ.get('ANDROID_SERIAL', '')
if not SERIAL:
    raise RuntimeError('Set ANDROID_SERIAL to the intended phone from adb devices -l.')

def adb(*args, data=None, timeout=25):
    result = subprocess.run([str(ADB), '-s', SERIAL, *args], input=data,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace'))
    return result.stdout

def ui():
    adb('shell', 'uiautomator', 'dump', '/data/local/tmp/halow-ui.xml')
    return ET.fromstring(adb('shell', 'cat', '/data/local/tmp/halow-ui.xml'))

def describe():
    for node in ui().iter('node'):
        a = node.attrib
        if a.get('text') or a.get('content-desc') or a.get('clickable') == 'true' or a.get('checkable') == 'true' or a.get('class') == 'android.widget.SeekBar':
            print(json.dumps({k: ('[hidden]' if k == 'text' and a.get('password') == 'true' else a.get(k, ''))
                              for k in ('text', 'resource-id', 'content-desc', 'class', 'bounds', 'checked', 'clickable')}, ensure_ascii=False))

def tap_id(resource_id):
    matches = [n for n in ui().iter('node') if n.get('resource-id') == resource_id]
    if len(matches) != 1:
        raise RuntimeError('Expected one visible target: ' + resource_id)
    x1, y1, x2, y2 = map(int, re.findall(r'\d+', matches[0].get('bounds')))
    adb('shell', 'input', 'tap', str((x1+x2)//2), str((y1+y2)//2))

def tap_attribute(attribute,value):
    matches=[n for n in ui().iter('node') if n.get(attribute)==value]
    if len(matches)!=1:raise RuntimeError('Expected one visible target: '+value)
    x1,y1,x2,y2=map(int,re.findall(r'\d+',matches[0].get('bounds')))
    adb('shell','input','tap',str((x1+x2)//2),str((y1+y2)//2))

def set_field(resource_id, value):
    tap_id(resource_id)
    adb('shell', 'input', 'keycombination', '113', '29')
    adb('shell', 'input', 'keyevent', '67')
    adb('shell', 'input', 'text', shlex.quote(value))
    adb('shell', 'input', 'keyevent', '4')

if __name__ == '__main__':
    if sys.argv[1] == 'ui':
        describe()
    elif sys.argv[1] == 'tap-id':
        tap_id(sys.argv[2])
        describe()
    elif sys.argv[1] in ('tap-text','tap-desc'):
        tap_attribute('text' if sys.argv[1]=='tap-text' else 'content-desc',sys.argv[2])
        describe()
    elif sys.argv[1] == 'complete-server':
        before = {n.get('resource-id'): n.get('text') for n in ui().iter('node')}
        if before.get('se.lublin.mumla:id/server_edit_host') != '10.42.0.137':
            raise RuntimeError('Unexpected server address; no edits made.')
        password = json.loads((BASE/'private/credentials.json').read_text())['mumble_password']
        set_field('se.lublin.mumla:id/server_edit_port', '64738')
        set_field('se.lublin.mumla:id/server_edit_password', password)
        tap_id('android:id/button1')
        print('Saved the existing server entry with port 64738 and the private server password.')
        describe()
    else:
        raise SystemExit('Unknown operation')
