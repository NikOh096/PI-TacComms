"""Small CDP client scoped to the phone's HD01 configuration tab."""
import base64,hashlib,json,os,socket,struct,sys,urllib.request
TAB_ID='7533'  # Existing local Heltec setup tab, observed through CDP.

def readn(sock,n):
    data=b''
    while len(data)<n:
        part=sock.recv(n-len(data))
        if not part:raise EOFError('Browser debugger closed')
        data+=part
    return data
def evaluate(expression):
    targets=json.load(urllib.request.urlopen('http://127.0.0.1:9222/json',timeout=8))
    pages=[p for p in targets if p.get('url','').startswith(('http://10.42.0.1/','http://192.168.100.1/'))]
    if TAB_ID:pages=[p for p in pages if p.get('id')==TAB_ID]
    if len(pages)!=1:raise RuntimeError('Expected exactly one local HD01 setup tab')
    path='/devtools/page/'+pages[0]['id']
    with socket.create_connection(('127.0.0.1',9222),timeout=20) as sock:
        key=base64.b64encode(os.urandom(16)).decode()
        sock.sendall((f'GET {path} HTTP/1.1\r\nHost: localhost:9222\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        head=b''
        while not head.endswith(b'\r\n\r\n'):head+=readn(sock,1)
        assert head.split(b' ',2)[1]==b'101',head[:50]
        expected=base64.b64encode(hashlib.sha1((key+'258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
        assert expected.lower() in head.lower()
        for command in ({'id':2,'method':'Page.bringToFront'},
                        {'id':1,'method':'Runtime.evaluate','params':{'expression':expression,'awaitPromise':True,'returnByValue':True}}):
            message=json.dumps(command).encode()
            n=len(message);mask=os.urandom(4)
            frame=bytes([0x81,0x80|n]) if n<126 else b'\x81\xfe'+struct.pack('!H',n) if n<65536 else b'\x81\xff'+struct.pack('!Q',n)
            sock.sendall(frame+mask+bytes(v^mask[i%4] for i,v in enumerate(message)))
        fragments=b''
        while True:
            a,b=readn(sock,2);n=b&127
            if n==126:n=struct.unpack('!H',readn(sock,2))[0]
            elif n==127:n=struct.unpack('!Q',readn(sock,8))[0]
            assert n<2_000_000
            mask=readn(sock,4) if b&128 else None;data=readn(sock,n)
            if mask:data=bytes(v^mask[i%4] for i,v in enumerate(data))
            if a&15==8:raise EOFError('Debugger closed')
            if a&15 not in (0,1):continue
            fragments+=data
            if not a&128:continue
            value=json.loads(fragments);fragments=b''
            if value.get('id')==1:
                result=value['result']
                if 'exceptionDetails' in result:
                    detail=result['exceptionDetails'].get('exception',{}).get('description','Browser expression failed').splitlines()[0]
                    raise RuntimeError(detail)
                return result['result'].get('value')

def rpc(sid,obj,method,args):
    payload={'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]}
    expression='(async()=>{const r=await fetch("/ubus",{method:"POST",signal:AbortSignal.timeout(8000),headers:{"Content-Type":"application/json"},body:'+json.dumps(json.dumps(payload))+'});return await r.json();})()'
    value=evaluate(expression); result=value.get('result',[])
    if not result or result[0]!=0:raise RuntimeError(obj+'.'+method+' failed: '+str(result[:1] or value.get('error')))
    return result[1] if len(result)>1 else {}

if __name__=='__main__':
    print(evaluate('JSON.stringify({title:document.title,text:document.body.innerText.slice(0,4000),inputs:[...document.querySelectorAll("input")].map(x=>({type:x.type,name:x.name,value:x.type==="password"?"[hidden]":x.value}))})'))
