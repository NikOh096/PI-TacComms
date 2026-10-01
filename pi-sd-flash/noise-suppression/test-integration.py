"""Loopback-only Mumble integration. Never opens the production database/config.

Test-only legacy OCB2 framing follows Mumble's CryptStateOCB2 implementation;
AES comes from OpenSSL. This is not a reusable or production crypto module.
"""
import ctypes as C
import hashlib,hmac,json,math,os,secrets,select,socket,ssl,struct,subprocess,tempfile,time
from pathlib import Path

BASE=Path('/home/niko/taccomms-noise-build')
PORT=64749
ICEPORT=6509

def pv(n):
    out=bytearray()
    while n>127:out.append((n&127)|128);n>>=7
    return bytes(out)+bytes([n])
def pi(f,n):return pv(f*8)+pv(n)
def ps(f,s):
    s=s.encode() if isinstance(s,str) else s
    return pv(f*8+2)+pv(len(s))+s
def fields(data):
    def var(offset):
        n=shift=0
        while True:
            b=data[offset];offset+=1;n|=(b&127)<<shift
            if not b&128:return n,offset
            shift+=7;assert shift<=70
    result={};offset=0
    while offset<len(data):
        tag,offset=var(offset);wire=tag&7;field=tag>>3
        if wire==0:value,offset=var(offset)
        elif wire==2:
            length,offset=var(offset);value=data[offset:offset+length];offset+=length
        elif wire in (1,5):
            length=8 if wire==1 else 4;value=data[offset:offset+length];offset+=length
        else:raise AssertionError('Unknown protobuf wire type')
        result[field]=value
    return result
def mv(n):
    if n<128:return bytes([n])
    if n<16384:return bytes([0x80|(n>>8),n&255])
    if n<2097152:return bytes([0xc0|(n>>16),(n>>8)&255,n&255])
    return b'\xf0'+struct.pack('>I',n)
def unmv(data,offset):
    first=data[offset];offset+=1
    if first<128:return first,offset
    if first<192:n,extra=first&63,1
    elif first<224:n,extra=first&31,2
    elif first<240:n,extra=first&15,3
    elif first==240:n,extra=0,4
    elif first==244:n,extra=0,8
    else:raise AssertionError('Unexpected Mumble varint')
    for b in data[offset:offset+extra]:n=(n<<8)|b
    return n,offset+extra
def parse_audio(data):
    assert data[0]>>5==4
    sid,o=unmv(data,1);seq,o=unmv(data,o);length,o=unmv(data,o)
    return sid,seq,data[o:o+(length&8191)],bool(length&8192)

crypto=C.CDLL('libcrypto.so.3')
crypto.EVP_CIPHER_CTX_new.restype=C.c_void_p
crypto.EVP_aes_128_ecb.restype=C.c_void_p
crypto.EVP_CIPHER_CTX_set_padding.argtypes=[C.c_void_p,C.c_int]
crypto.EVP_CIPHER_CTX_free.argtypes=[C.c_void_p]
for name in ('Encrypt','Decrypt'):
    getattr(crypto,'EVP_'+name+'Init_ex').argtypes=[C.c_void_p,C.c_void_p,C.c_void_p,C.c_char_p,C.c_void_p]
    getattr(crypto,'EVP_'+name+'Update').argtypes=[C.c_void_p,C.c_void_p,C.POINTER(C.c_int),C.c_char_p,C.c_int]
MASK=(1<<128)-1
def double(n):return ((n<<1)&MASK)^(0x87 if n>>127 else 0)
class OCB:
    def __init__(self,key,enc,dec):
        self.enc=int.from_bytes(enc,'little');self.dec=int.from_bytes(dec,'little')
        self.contexts={}
        for name in ('Encrypt','Decrypt'):
            ctx=crypto.EVP_CIPHER_CTX_new();self.contexts[name]=ctx
            assert getattr(crypto,'EVP_'+name+'Init_ex')(ctx,crypto.EVP_aes_128_ecb(),None,key,None)==1
            assert crypto.EVP_CIPHER_CTX_set_padding(ctx,0)==1
    def aes(self,value,encrypt=True):
        name='Encrypt' if encrypt else 'Decrypt';out=C.create_string_buffer(32);length=C.c_int()
        assert getattr(crypto,'EVP_'+name+'Update')(self.contexts[name],out,C.byref(length),value.to_bytes(16,'big'),16)==1
        assert length.value==16
        return int.from_bytes(out.raw[:16],'big')
    def encrypt(self,data):
        self.enc=(self.enc+1)&MASK
        nonce=self.enc.to_bytes(16,'little');delta=self.aes(int.from_bytes(nonce,'big'));checksum=0;out=b''
        while len(data)>16:
            block=int.from_bytes(data[:16],'big')
            assert not (len(data)<=32 and data[:15]==bytes(15)),'Test packet triggers OCB2 countermeasure'
            delta=double(delta);out+=(self.aes(block^delta)^delta).to_bytes(16,'big');checksum^=block;data=data[16:]
        delta=double(delta);pad=self.aes(delta^(len(data)*8)).to_bytes(16,'big')
        block=int.from_bytes(data+pad[len(data):],'big');checksum^=block
        out+=bytes(a^b for a,b in zip(data,pad))
        tag=self.aes(delta^double(delta)^checksum).to_bytes(16,'big')
        return nonce[:1]+tag[:3]+out
    def decrypt(self,packet):
        assert packet[0]==((self.dec+1)&255),'Test expects in-order loopback packets'
        self.dec=(self.dec+1)&MASK;nonce=self.dec.to_bytes(16,'little')
        data=packet[4:];delta=self.aes(int.from_bytes(nonce,'big'));checksum=0;out=b''
        while len(data)>16:
            delta=double(delta);block=self.aes(int.from_bytes(data[:16],'big')^delta,False)^delta
            checksum^=block;out+=block.to_bytes(16,'big');data=data[16:]
        delta=double(delta);pad=self.aes(delta^(len(data)*8))
        block=int.from_bytes(data+bytes(16-len(data)),'big')^pad
        assert block.to_bytes(16,'big')[:15]!=delta.to_bytes(16,'big')[:15]
        checksum^=block;out+=block.to_bytes(16,'big')[:len(data)]
        tag=self.aes(delta^double(delta)^checksum).to_bytes(16,'big')
        assert hmac.compare_digest(tag[:3],packet[1:4])
        return out
    def close(self):
        for ctx in self.contexts.values():crypto.EVP_CIPHER_CTX_free(ctx)

class Client:
    def __init__(self,name,password,accept=True):
        self.buffer=b'';self.ocb=None;self.udp=None
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT);ctx.check_hostname=False;ctx.verify_mode=ssl.CERT_NONE
        self.tcp=ctx.wrap_socket(socket.create_connection(('127.0.0.1',PORT),timeout=4),server_hostname='isolated-test')
        self.send(0,pi(1,0x010400)+ps(2,'TacComms isolated integration'))
        self.send(2,ps(1,name)+ps(2,password)+pi(5,1))
        while True:
            item=self.recv(5);assert item is not None,'Handshake timed out'
            kind,data=item;f=fields(data)
            if kind==4:
                assert not accept,'Login rejected';self.sid=None;return
            if kind==15:self.ocb=OCB(f[1],f[2],f[3])
            if kind==5:
                assert accept,'Incorrect password accepted';self.sid=f[1];return
    def send(self,kind,data):self.tcp.sendall(struct.pack('>HI',kind,len(data))+data)
    def recv(self,timeout=.15):
        until=time.monotonic()+timeout
        while True:
            if len(self.buffer)>=6:
                kind,size=struct.unpack('>HI',self.buffer[:6]);assert size<1000000
                if len(self.buffer)>=size+6:
                    data=self.buffer[6:6+size];self.buffer=self.buffer[6+size:];return kind,data
            left=until-time.monotonic()
            if left<=0:return None
            if not self.tcp.pending() and not select.select([self.tcp],[],[],left)[0]:return None
            data=self.tcp.recv(65536);assert data,'Socket closed';self.buffer+=data
    def audio(self,timeout=.5):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            item=self.recv(until-time.monotonic())
            if item is None:return None
            if item[0]==1:return parse_audio(item[1])
        return None
    def drain(self):
        while self.recv(.02) is not None:pass
    def use_udp(self):
        assert self.ocb
        self.udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);self.udp.settimeout(2)
        ping=b'\x20'+mv(123)
        self.udp.sendto(self.ocb.encrypt(ping),('127.0.0.1',PORT))
        response=self.ocb.decrypt(self.udp.recv(2048));assert response==ping
    def send_audio(self,payload,seq,last=False):
        packet=b'\x80'+mv(seq)+mv(len(payload)|(8192 if last else 0))+payload
        if self.udp:self.udp.sendto(self.ocb.encrypt(packet),('127.0.0.1',PORT))
        else:self.send(1,packet)
    def close(self):
        self.tcp.close()
        if self.udp:self.udp.close()
        if self.ocb:self.ocb.close()

opus=C.CDLL('libopus.so.0')
opus.opus_encoder_create.restype=C.c_void_p;opus.opus_encoder_create.argtypes=[C.c_int,C.c_int,C.c_int,C.POINTER(C.c_int)]
opus.opus_encode_float.argtypes=[C.c_void_p,C.POINTER(C.c_float),C.c_int,C.c_void_p,C.c_int]
opus.opus_encoder_destroy.argtypes=[C.c_void_p]
opus.opus_packet_get_nb_samples.argtypes=[C.c_char_p,C.c_int,C.c_int]
error=C.c_int();enc=opus.opus_encoder_create(48000,1,2048,C.byref(error));assert enc and not error.value
def voice(frame):
    pcm=(C.c_float*960)(*(.08*math.sin(2*math.pi*250*(frame*960+i)/48000)+.01*math.sin(i*.927) for i in range(960)))
    buf=C.create_string_buffer(1275);size=opus.opus_encode_float(enc,pcm,960,buf,1275);assert size>0
    return buf.raw[:size]

clients=[];process=None;ice=None
temp=Path(tempfile.mkdtemp(prefix='integration-',dir=BASE));os.chmod(temp,0o700)
try:
    password=secrets.token_hex(16);secret=secrets.token_hex(16)
    config=temp/'mumble.ini';mode=temp/'noise.conf';mode.write_text('off\n')
    config.write_text(f'host=127.0.0.1\nport={PORT}\ndatabase={temp}/db.sqlite\nlogfile={temp}/server.log\nserverpassword={password}\nusers=8\nbandwidth=128000\nice="tcp -h 127.0.0.1 -p {ICEPORT}"\nicesecretread={secret}\nicesecretwrite={secret}\n')
    log=(temp/'process.log').open('w')
    process=subprocess.Popen([str(BASE/'build/mumble-server'),'-fg','-ini',str(config)],stdout=log,stderr=log,env=dict(os.environ,TACCOMMS_NOISE_CONFIG=str(mode)))
    for _ in range(100):
        assert process.poll() is None,'Isolated server exited: '+(temp/'process.log').read_text()[-2000:]
        try:
            with socket.create_connection(('127.0.0.1',PORT),timeout=.2):break
        except OSError:time.sleep(.1)
    rejected=Client('WrongPassword','wrong',accept=False);clients.append(rejected)
    sender=Client('Speaker',password);listener=Client('Listener',password);outsider=Client('OtherChannel',password)
    clients.extend((sender,listener,outsider))
    import Ice
    Ice.loadSlice('-I/usr/share/ice/slice /usr/share/mumble-server/MumbleServer.ice')
    import MumbleServer
    ice=Ice.initialize(['isolated-test','--Ice.Warn.Connections=0'])
    server=MumbleServer.ServerPrx.uncheckedCast(ice.stringToProxy(f's/1:tcp -h 127.0.0.1 -p {ICEPORT}')).ice_context({'secret':secret}).ice_invocationTimeout(3000)
    other=server.addChannel('Other',0);u=server.getState(outsider.sid);u.channel=other;server.setState(u)
    for c in (sender,listener,outsider):c.drain()
    raw=voice(0);sender.send_audio(raw,0);received=listener.audio()
    assert received and received[:3]==(sender.sid,0,raw),'Off mode not bit-identical'
    assert outsider.audio(.1) is None,'Audio leaked to another channel'
    mode.write_text('on\n');time.sleep(1.2)
    raw=voice(1);sender.send_audio(raw,2);received=listener.audio()
    assert received and received[0:2]==(sender.sid,2) and received[2]!=raw,'TCP filter or speaker identity failed'
    assert opus.opus_packet_get_nb_samples(received[2],len(received[2]),48000)==960
    sender.use_udp();raw=voice(2);sender.send_audio(raw,4);received=listener.audio()
    assert received and received[0:2]==(sender.sid,4) and received[2]!=raw,'UDP to TCP filtering failed'
    listener.use_udp();raw=voice(3);sender.send_audio(raw,6,True)
    received=parse_audio(listener.ocb.decrypt(listener.udp.recv(2048)))
    assert received[0:2]==(sender.sid,6) and received[2]!=raw and received[3],'Encrypted UDP/filter/end marker failed'
    assert outsider.audio(.1) is None,'Filtered audio leaked to another channel'
    u=server.getState(sender.sid);u.mute=True;server.setState(u);time.sleep(.05)
    sender.send_audio(voice(4),8)
    listener.udp.settimeout(.25)
    try:listener.udp.recv(2048)
    except socket.timeout:pass
    else:raise AssertionError('Server mute bypassed')
    assert process.poll() is None
    result={'passed':True,'isolated_server':True,'production_server_modified':False,
            'binary_sha256':hashlib.sha256((BASE/'build/mumble-server').read_bytes()).hexdigest(),
            'password_rejection':True,'tcp_voice_filter':True,'udp_to_tcp_voice_filter':True,
            'encrypted_udp_voice_filter':True,'speaker_identity_and_end_marker':True,
            'channel_isolation':True,'server_mute':True,'disabled_bit_identical':True}
    (BASE/'integration-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
finally:
    for c in clients:c.close()
    if ice:ice.destroy()
    if process:
        process.terminate()
        try:process.wait(6)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    opus.opus_encoder_destroy(enc)
