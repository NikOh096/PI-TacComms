"""Read the HD01 web UI through the phone's explicitly bound Wi-Fi address."""
import importlib.util
from pathlib import Path

base = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('phone', base/'android-phone.py')
phone = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phone)
request = b'GET / HTTP/1.1\r\nHost: 10.42.0.1\r\nConnection: close\r\n\r\n'
try:
    response = phone.adb('shell', 'toybox', 'nc', '-s', '10.42.0.151', '-w', '5', '-W', '5', '-q', '3', '10.42.0.1', '80', data=request)
    (base/'android-tools/hd01-root.http').write_bytes(response)
    print(response[:2500].decode(errors='replace'))
except Exception as error:
    print(type(error).__name__, str(error))
