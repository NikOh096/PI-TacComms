import concurrent.futures
import hashlib
import json
import lzma
import pathlib
import sys
import urllib.request

BASE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(BASE / 'setup-tools'))
from debian.deb822 import Deb822, PkgRelation
from debian.debian_support import Version

installed = {p['Package']: p for p in Deb822.iter_paragraphs((BASE / 'card-inventory/var__lib__dpkg__status').read_text(encoding='utf-8')) if p.get('Status') == 'install ok installed'}
with lzma.open(BASE / 'package-indexes/debian-main-Packages.xz', 'rt', encoding='utf-8') as index:
    available = {p['Package']: p for p in Deb822.iter_paragraphs(index)}
selected = {}

def relations(text):
    return PkgRelation.parse_relations(text) if text.strip() else []

def matches(package, relation):
    constraint = relation.get('version')
    if not constraint: return True
    operator, wanted = constraint
    actual, wanted = Version(package['Version']), Version(wanted)
    return {'>=': actual >= wanted, '<=': actual <= wanted, '=': actual == wanted, '>>': actual > wanted, '<<': actual < wanted}[operator]

def provided(records, relation):
    name = relation['name']
    if name in records and matches(records[name], relation): return True
    for package in records.values():
        for group in relations(package.get('Provides', '')):
            for offer in group:
                if offer['name'] == name and (not relation.get('version') or (offer.get('version') and matches({'Version': offer['version'][1]}, relation))): return True
    return False

def require(name):
    if name in selected: return
    if name not in available: raise RuntimeError(f'Package unavailable: {name}')
    package = available[name]
    if package.get('Architecture') not in ('arm64', 'all'): raise RuntimeError('Unexpected architecture')
    selected[name] = package
    for field in ('Pre-Depends', 'Depends'):
        for alternatives in relations(package.get(field, '')):
            if any(provided(selected, r) or provided(installed, r) for r in alternatives): continue
            for relation in alternatives:
                target = available.get(relation['name'])
                if target and matches(target, relation):
                    require(relation['name'])
                    break
            else: raise RuntimeError(f'Unresolved dependency of {name}: {alternatives}')

for name in ('mumble-server', 'mumble', 'evtest', 'ddcutil'):
    require(name)
for package in selected.values():
    for field in ('Pre-Depends', 'Depends'):
        for alternatives in relations(package.get(field, '')):
            if not any(provided(selected, r) or (r['name'] not in selected and provided(installed, r)) for r in alternatives):
                raise RuntimeError(f'Final dependency check failed for {package["Package"]}: {alternatives}')

folder = BASE / 'halow-setup/debs'
folder.mkdir(parents=True, exist_ok=True)
manifest = []
for name, package in sorted(selected.items()):
    record = {'name': name, 'version': package['Version'], 'filename': pathlib.PurePosixPath(package['Filename']).name, 'url': 'https://deb.debian.org/debian/' + package['Filename'], 'sha256': package['SHA256'], 'size': int(package['Size']), 'was_installed': name in installed}
    manifest.append(record)
(folder.parent / 'packages.json').write_text(json.dumps(manifest, indent=2))
print(json.dumps({'packages': [{k: r[k] for k in ('name','version','was_installed')} for r in manifest], 'download_bytes': sum(r['size'] for r in manifest)}, indent=2), flush=True)

def download(record):
    target = folder / record['filename']
    if not target.exists() or hashlib.sha256(target.read_bytes()).hexdigest() != record['sha256']:
        with urllib.request.urlopen(record['url'], timeout=90) as response:
            target.write_bytes(response.read())
    if target.stat().st_size != record['size'] or hashlib.sha256(target.read_bytes()).hexdigest() != record['sha256']:
        raise RuntimeError('Package integrity check failed: ' + record['name'])
    return record['name']

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for name in pool.map(download, manifest): print('Verified:', name, flush=True)
(folder.parent / 'SHA256SUMS').write_text(''.join(r['sha256'] + '  debs/' + r['filename'] + '\n' for r in manifest))
print('Offline package bundle ready.', flush=True)
