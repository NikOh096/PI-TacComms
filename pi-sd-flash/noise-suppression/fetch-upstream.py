"""Restore pinned audio-build inputs without executing upstream code (Python 3.12+)."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import urllib.request

BASE = Path(__file__).resolve().parent


def valid(path, item):
    if not path.is_file() or path.stat().st_size != item['size']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == item['sha256']


def restore(item, cache, verify_only):
    destination = BASE / item['filename']
    source = cache / item['filename'] if cache else destination
    if verify_only:
        if not valid(source, item):
            raise RuntimeError('Missing or mismatched archive: ' + item['filename'])
        print('Verified', item['filename'])
        return
    if valid(destination, item):
        return
    temporary = destination.with_suffix(destination.suffix + '.partial')
    try:
        if cache and valid(source, item):
            shutil.copyfile(source, temporary)
        else:
            request = urllib.request.Request(item['url'], headers={'User-Agent': 'TacComms-source-restore'})
            with urllib.request.urlopen(request, timeout=90) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
        if not valid(temporary, item):
            raise RuntimeError('Size or SHA-256 mismatch: ' + item['filename'])
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print('Restored', item['filename'])


def extract(archive_name, target):
    target.mkdir(parents=True, exist_ok=True)
    with tarfile.open(BASE / archive_name) as archive:
        archive.extractall(target, filter='data')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, help='Use matching archives from a prior machine')
    parser.add_argument('--verify-only', action='store_true', help='Check hashes without downloading or extracting')
    parser.add_argument('--extract', action='store_true', help='Extract verified sources into ignored inspect/')
    args = parser.parse_args()
    if args.verify_only and args.extract:
        parser.error('--verify-only cannot be combined with --extract')
    manifest = json.loads((BASE / 'upstream-artifacts.json').read_text())
    for item in manifest['artifacts']:
        restore(item, args.cache, args.verify_only)
    if args.extract:
        inspect = BASE / 'inspect'
        # Never overwrite modified research sources from an earlier checkout.
        if inspect.exists():
            raise RuntimeError('inspect/ already exists. Review or preserve it before extracting fresh inputs.')
        extract('mumble_1.5.735.orig.tar.gz', inspect)
        extract('opus-1.5.2.tar.gz', inspect)
        extract('rnnoise-modern.tar.gz', inspect)
        extract('rnnoise-modern-model.tar.gz', inspect / ('rnnoise-' + manifest['rnnoise_revision']))
        print('Extracted verified upstream sources. No patches, builds or installations were run.')


if __name__ == '__main__':
    main()
