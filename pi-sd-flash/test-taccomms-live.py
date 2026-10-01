import datetime, hashlib, json, os, socket, ssl, struct, subprocess, sys, tempfile, time
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from backend import Mumble,Admin
from client import request
from security import SecurityStore,SecurityError
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa

assert not request('state')['enrolled']
try: request('command',line='status',token='untrusted')
except RuntimeError: pass
else: raise AssertionError('Unauthenticated admin request accepted')
m=Mumble()
main=m.server()
print('Production Mumble running:',main.isRunning(),'Connected clients:',len(main.getUsers()))
import MumbleServer
meta=MumbleServer.MetaPrx.uncheckedCast(m.ice.stringToProxy('Meta:tcp -h 127.0.0.1 -p 6502')).ice_context({'secret':m.secret}).ice_invocationTimeout(3000)
# Previous attempt created server 2 but its returned proxy did not inherit the
# authentication context. Remove that known, never-started empty test instance.
orphan=meta.getServer(2)
if orphan:
    orphan=orphan.ice_context({'secret':m.secret}).ice_invocationTimeout(3000)
    assert not orphan.isRunning() and not orphan.getAllConf(), 'Unexpected test-server state'
    orphan.delete()
test=meta.newServer().ice_context({'secret':m.secret}).ice_invocationTimeout(3000)
connections=[]

def vint(n):
    out=bytearray()
    while n>127: out.append((n&127)|128); n>>=7
    out.append(n); return bytes(out)
def txt(field,value):
    value=value.encode(); return vint(field*8+2)+vint(len(value))+value
def packet(conn,kind,data): conn.sendall(struct.pack('!HI',kind,len(data))+data)
def readn(conn,count):
    result=b''
    while len(result)<count:
        part=conn.recv(count-len(result))
        if not part: raise EOFError()
        result+=part
    return result
def certificate(folder,name):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    subject=x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,name)])
    now=datetime.datetime.now(datetime.timezone.utc)
    cert=x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(now-datetime.timedelta(minutes=5)).not_valid_after(now+datetime.timedelta(days=1)).sign(key,hashes.SHA256())
    cp=folder/(name+'.crt'); kp=folder/(name+'.key')
    cp.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    kp.write_bytes(key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption())); kp.chmod(0o600)
    return str(cp),str(kp)
def connect(name,password,cert):
    ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    ctx.load_cert_chain(*cert)
    conn=ctx.wrap_socket(socket.create_connection(('127.0.0.1',64749),timeout=3),server_hostname='localhost')
    packet(conn,0,b'\x08'+vint(0x10500)+txt(2,'TacComms self-test'))
    packet(conn,2,txt(1,name)+txt(2,password)+b'\x28\x01')
    try:
        for _ in range(100):
            kind,length=struct.unpack('!HI',readn(conn,6)); payload=readn(conn,length)
            if kind==4: conn.close(); return None
            if kind==5: connections.append(conn); return conn
    except (EOFError,ssl.SSLError,ConnectionResetError):
        conn.close(); return None
    raise AssertionError('Missing Mumble sync')

try:
    test.setConf('boot','false'); test.setConf('host','127.0.0.1'); test.setConf('port','64749')
    test.setConf('password','Test-only-random-voice'); test.start()
    with tempfile.TemporaryDirectory(prefix='taccomms-check-') as tmp:
        folder=Path(tmp); cert_a=certificate(folder,'test-a'); cert_b=certificate(folder,'test-b')
        assert connect('test-a','wrong',cert_a) is None
        one=connect('test-a','Test-only-random-voice',cert_a); assert one
        one.close(); time.sleep(.1)
        test.setConf('password','')
        one=connect('test-a','',cert_a)
        assert one,'Clearing password inherited original default instead of removing password'
        one.close(); test.stop(); test.start()
        one=connect('test-a','',cert_a); assert one,'Password clear did not persist after server restart'
        two=connect('test-b','',cert_b); assert two
        sid=next(i for i,u in test.getUsers().items() if u.name=='test-a')
        m.server=lambda:test
        secure=SecurityStore(folder/'security'); secure.enroll('142857','142857','963852','963852')
        app=Admin(mumble=m,security=secure); token=secure.login('142857',0)
        def cmd(line,confirm=False):
            answer=app.dispatch({'op':'command','token':token,'line':line},0,0)
            if confirm:
                assert answer.get('confirm')
                answer=app.dispatch({'op':'confirm','token':token,'id':answer['confirm']},0,0)
            return answer
        assert len(cmd('users')['users'])==2
        cid=int(cmd('channel add 0 "Test Room"')['lines'][0].split(': ')[1])
        cmd('channel rename '+str(cid)+' "Renamed"')
        cmd(f'move {sid} {cid}'); assert test.getState(sid).channel==cid
        cmd(f'mute {sid} on'); assert test.getState(sid).mute
        cmd(f'mute {sid} off'); assert not test.getState(sid).mute
        cmd(f'deafen {sid} on'); assert test.getState(sid).deaf
        cmd(f'deafen {sid} off'); cmd(f'mute {sid} off')
        cmd(f'priority {sid} on'); assert test.getState(sid).prioritySpeaker
        cmd(f'register {sid}'); registered=test.getRegisteredUsers('test-a'); assert registered
        identity=next(iter(registered))
        fingerprint=m.cert(sid)
        cmd(f'ban {sid} test',True)
        assert connect('test-a','',cert_a) is None,'Certificate ban did not reject identity'
        assert any(u.name=='test-b' for u in test.getUsers().values()),'Certificate ban affected other same-IP client'
        cmd('unban '+fingerprint,True)
        one=connect('test-a','',cert_a); assert one
        cmd('revoke '+str(identity),True)
        assert connect('test-a','',cert_a) is None
        assert identity not in test.getRegisteredUsers('')
        cmd('channel delete '+str(cid),True); assert cid not in test.getChannels()
        secure.emergency()
        try: cmd('password clear',True)
        except SecurityError: pass
        else: raise AssertionError('Emergency mode accepted command')
        assert test.isRunning() and main.isRunning()
        print('PASS: TLS/password persistence, channels, mute/deafen/move/priority, certificate register/ban/unban/revoke, same-IP isolation, emergency command denial.')
finally:
    for conn in connections: conn.close()
    try:
        if test.isRunning(): test.stop()
        test.delete()
    finally: m.ice.destroy()
print('Temporary test server removed. Production voice service remains running.')
