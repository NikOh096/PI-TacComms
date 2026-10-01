"""Check login and UDP reachability on the verified, directly attached Pi USB link."""
import hashlib
import json
from pathlib import Path
import secrets
import socket
import ssl
import struct
import time

base = Path(__file__).resolve().parent
password = json.loads((base / 'private/credentials.json').read_text())['mumble_password']
def varint(value):
    result = bytearray()
    while value > 127:
        result.append((value & 127) | 128)
        value >>= 7
    return bytes(result) + bytes([value])
def string(field, value):
    raw = value.encode()
    return varint(field * 8 + 2) + varint(len(raw)) + raw
def integer(field, value):
    return varint(field * 8) + varint(value)
def receive(connection, size):
    result = b''
    while len(result) < size:
        block = connection.recv(size-len(result))
        if not block:
            raise RuntimeError('Server closed the test connection')
        result += block
    return result
def send(connection, kind, message):
    connection.sendall(struct.pack('>HI',kind,len(message)) + message)

# Mumble uses a self-signed certificate. The endpoint is the Pi already authenticated
# by its pinned SSH host key on a direct USB cable; record its TLS identity for clients.
context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
context.check_hostname = False
context.verify_mode = ssl.CERT_NONE
with socket.create_connection(('10.12.194.1',64738), timeout=8) as raw:
    with context.wrap_socket(raw, server_hostname='halow-pi') as connection:
        fingerprint = hashlib.sha256(connection.getpeercert(binary_form=True)).hexdigest()
        send(connection, 0, integer(1, 0x010500) + string(2, 'HaLow setup test') + string(3,'Windows'))
        send(connection, 2, string(1,'Setup-connection-test') + string(2,password) + integer(5,1))
        authenticated = False
        for _ in range(40):
            kind, length = struct.unpack('>HI',receive(connection,6))
            if length > 1_000_000:
                raise RuntimeError('Unexpected packet length')
            message = receive(connection,length)
            if kind == 4:
                raise RuntimeError('Server rejected the test login')
            if kind == 5:
                authenticated = True
                break
        if not authenticated:
            raise RuntimeError('No authenticated ServerSync received')
nonce = secrets.randbits(64)
with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
    udp.settimeout(5)
    udp.sendto(struct.pack('>IQ',0,nonce), ('10.12.194.1',64738))
    data, address = udp.recvfrom(2048)
    assert address == ('10.12.194.1',64738) and len(data) == 24
    version, reply_nonce, users, max_users, bandwidth = struct.unpack('>IQIII',data)
    assert reply_nonce == nonce
result = {'tcp_tls_login':authenticated,'udp_ping':True,'server_certificate_sha256':fingerprint,
          'tested_at':time.time(),'ethernet_phone_path_tested':False,'audio_call_tested':False}
(base/'mumble-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print('PASS: authenticated Mumble login over TLS and UDP ping from this PC to the Pi.')
print('Phone-to-phone audio over HaLow still requires a call test.')
