import base64, hashlib, os
from pathlib import Path
data = base64.b64decode('W1VuaXRdCkRlc2NyaXB0aW9uPVRhY0NvbW1zIHNlY3VyZSB0b3VjaHNjcmVlbgpBZnRlcj10YWNjb21tcy1hZG1pbi5zZXJ2aWNlIHN5c3RlbWQtdXNlci1zZXNzaW9ucy5zZXJ2aWNlIGNvbnNvbGUtc2V0dXAuc2VydmljZQpXYW50cz10YWNjb21tcy1hZG1pbi5zZXJ2aWNlCkNvbmZsaWN0cz1oYWxvdy1jb25zb2xlLnNlcnZpY2UgZ2V0dHlAdHR5MS5zZXJ2aWNlCgpbU2VydmljZV0KVHlwZT1zaW1wbGUKVXNlcj10YWNjb21tcwpHcm91cD10YWNjb21tcwpTdXBwbGVtZW50YXJ5R3JvdXBzPXZpZGVvIGlucHV0IGkyYyBncGlvIHR0eSBzeXN0ZW1kLWpvdXJuYWwKRXhlY1N0YXJ0UHJlPSsvdXNyL2Jpbi9jaHZ0IDEKRXhlY1N0YXJ0PS91c3IvYmluL3B5dGhvbjMgL29wdC90YWNjb21tcy9zY3JlZW4ucHkKUmVzdGFydD1vbi1mYWlsdXJlClJlc3RhcnRTZWM9MwpTdGF0ZURpcmVjdG9yeT10YWNjb21tcy11aQpTdGF0ZURpcmVjdG9yeU1vZGU9MDcwMApTdGFuZGFyZElucHV0PXR0eQpTdGFuZGFyZE91dHB1dD10dHkKU3RhbmRhcmRFcnJvcj1qb3VybmFsClRUWVBhdGg9L2Rldi90dHkxClRUWVJlc2V0PXllcwpUVFlWSGFuZ3VwPXllcwpFbnZpcm9ubWVudD1URVJNPWxpbnV4CkVudmlyb25tZW50PVBZVEhPTlVOQlVGRkVSRUQ9MQpOb05ld1ByaXZpbGVnZXM9eWVzClByaXZhdGVUbXA9eWVzClByb3RlY3RTeXN0ZW09c3RyaWN0ClByb3RlY3RIb21lPXllcwpSZWFkV3JpdGVQYXRocz0vdmFyL2xpYi90YWNjb21tcy11aQpQcm90ZWN0S2VybmVsVHVuYWJsZXM9eWVzClByb3RlY3RLZXJuZWxNb2R1bGVzPXllcwpQcm90ZWN0Q29udHJvbEdyb3Vwcz15ZXMKUmVzdHJpY3RTVUlEU0dJRD15ZXMKTG9ja1BlcnNvbmFsaXR5PXllcwpSZXN0cmljdEFkZHJlc3NGYW1pbGllcz1BRl9VTklYIEFGX05FVExJTksKU3lzdGVtQ2FsbEFyY2hpdGVjdHVyZXM9bmF0aXZlCgpbSW5zdGFsbF0KV2FudGVkQnk9bXVsdGktdXNlci50YXJnZXQK')
assert hashlib.sha256(data).hexdigest() == '45c45c5f89753af058e9c56ce79eddf7d87d7b87f77bee6fa3aa329f438c979c'
for name in ['/etc/systemd/system/taccomms-screen.service']:
    path = Path(name)
    original = path.with_name(path.name + '.before-repair')
    if path.exists() and not original.exists():
        original.write_bytes(path.read_bytes())
    path.write_bytes(data)
    path.chmod(0o755 if name.startswith('/usr/local/bin/') else 0o644)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '45c45c5f89753af058e9c56ce79eddf7d87d7b87f77bee6fa3aa329f438c979c'
    manifest = path.parent / 'BUNDLE-SHA256SUMS'
    if manifest.exists():
        lines = manifest.read_text().splitlines()
        lines = ['45c45c5f89753af058e9c56ce79eddf7d87d7b87f77bee6fa3aa329f438c979c' + '  ' + path.name if line.endswith('  ' + path.name) else line for line in lines]
        manifest.write_text('\n'.join(lines) + '\n')
    print('Deployed and verified:', name)
os.sync()
