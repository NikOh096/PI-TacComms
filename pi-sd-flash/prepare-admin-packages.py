import hashlib
import json
import lzma
from pathlib import Path
import sys
import urllib.request

base = Path(__file__).resolve().parent
sys.path.insert(0, str(base/'setup-tools'))
from debian.deb822 import Deb822

target = base/'taccomms-admin/debs'
target.mkdir(parents=True, exist_ok=True)
wanted = {'python3-zeroc-ice', 'libmcpp0', 'zeroc-ice-slice'}
records = []
with lzma.open(base/'package-indexes/debian-main-Packages.xz', 'rt', encoding='utf-8') as source:
    for package in Deb822.iter_paragraphs(source):
        if package['Package'] not in wanted:
            continue
        assert package['Architecture'] in ('arm64', 'all')
        name = Path(package['Filename']).name
        cached = target/name
        data = cached.read_bytes() if cached.exists() else b''
        if len(data) != int(package['Size']) or hashlib.sha256(data).hexdigest() != package['SHA256']:
            data = urllib.request.urlopen('https://deb.debian.org/debian/' + package['Filename'], timeout=180).read()
        assert len(data) == int(package['Size']) and hashlib.sha256(data).hexdigest() == package['SHA256']
        (target/name).write_bytes(data)
        records.append({'name': package['Package'], 'version': package['Version'], 'filename': name,
                        'sha256': package['SHA256'], 'depends': package.get('Depends', '')})
        print('Verified:', package['Package'], package['Version'])
assert {record['name'] for record in records} == wanted
(target.parent/'packages.json').write_text(json.dumps(records, indent=2) + '\n')
