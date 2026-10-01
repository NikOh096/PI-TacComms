"""One bounded request per local Unix socket connection."""
import json
import socket
import time


def wait_ready(timeout=30):
    """Only startup state queries retry; never replay an administrative command."""
    deadline=time.monotonic()+timeout
    while True:
        try:return request('state')
        except (FileNotFoundError,ConnectionRefusedError):
            if time.monotonic()>=deadline:
                raise RuntimeError('Admin service did not become ready within the startup deadline.')
            time.sleep(0.25)


def request(op, **fields):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(35)
        client.connect('/run/taccomms/admin.sock')
        client.sendall(json.dumps({'op':op, **fields}).encode()+b'\n')
        with client.makefile('rb') as stream:
            raw=stream.readline(131073)
        if len(raw)>131072:
            raise RuntimeError('Admin response too large.')
        answer=json.loads(raw)
        if not answer.get('ok'):
            raise RuntimeError(answer.get('error','Admin request failed.'))
        return answer
