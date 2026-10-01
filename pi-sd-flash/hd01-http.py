"""HTTP over the phone's USB-authorized ADB and dongle Wi-Fi link."""
import http.client,io,json,os,re,shutil,subprocess,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
ADB=os.environ.get('TACCOMMS_ADB') or shutil.which('adb') or str(BASE/'android-tools/platform-tools/adb.exe')
SERIAL=os.environ.get('ANDROID_SERIAL','')
if not SERIAL:
    raise RuntimeError('Set ANDROID_SERIAL to the intended phone from adb devices -l.')
def http(path='/',payload=None):
    status=subprocess.check_output([str(ADB),'-s',SERIAL,'shell','cmd','wifi','status'],text=True)
    if 'Wifi is connected to "HT-HD01-BFD0"' not in status:
        raise RuntimeError('Phone is not on the intended HD01 hotspot')
    ip=re.search(r'IP: /([0-9.]+)',status).group(1)
    body=b'' if payload is None else json.dumps(payload).encode()
    method='GET' if payload is None else 'POST'
    data=(f'{method} {path} HTTP/1.1\r\nHost: 10.42.0.1\r\nConnection: close\r\nContent-Type: application/json\r\nContent-Length: {len(body)}\r\n\r\n').encode()+body
    proc=subprocess.Popen([str(ADB),'-s',SERIAL,'shell','-T','toybox','nc','-s',ip,'-w','5','-W','8','10.42.0.1','80'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdin=proc.stdin
    try:
        stdin.write(data); stdin.flush()
        proc.stdin=None  # Do not send EOF/FIN before uhttpd has answered.
        out,err=proc.communicate(timeout=12)
    except subprocess.TimeoutExpired:
        proc.kill();out,err=proc.communicate()
    finally: stdin.close()
    if not out:raise RuntimeError('No HTTP response: '+err.decode(errors='replace')[:100])
    class BufferSocket:
        def makefile(self,*args):return io.BytesIO(out)
    response=http.client.HTTPResponse(BufferSocket());response.begin()
    content=response.read()
    return response.status,content
def rpc(sid,obj,method,args):
    code,body=http('/ubus',{'jsonrpc':'2.0','id':1,'method':'call','params':[sid,obj,method,args]})
    assert code==200
    value=json.loads(body);result=value.get('result',[])
    if not result or result[0]!=0:raise RuntimeError(obj+'.'+method+' failed: '+str(result[:1] or value.get('error')))
    return result[1] if len(result)>1 else {}
if __name__=='__main__':
    code,body=http()
    print('HTTP status',code,'bytes',len(body))
    print(body[:700].decode(errors='replace'))
