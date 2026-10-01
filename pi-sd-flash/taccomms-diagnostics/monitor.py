#!/usr/bin/python3
"""Bounded local diagnostics. No audio, PINs, passwords or process arguments."""
import argparse
import datetime
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import threading
import tempfile

DATA=Path('/var/lib/taccomms-diagnostics')
SERVICES=('mumble-server.service','taccomms-admin.service','taccomms-screen.service')
LIMIT=2*1024*1024

def read(path,default=''):
    try:return Path(path).read_text(errors='replace').strip()
    except OSError:return default

def command(*args,timeout=5,limit=24000):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
        return (r.stdout+r.stderr)[-limit:].strip()
    except (OSError,subprocess.TimeoutExpired) as exc:
        return type(exc).__name__

def atomic_json(path,value):
    path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,indent=2);stream.write('\n');stream.flush();os.fsync(stream.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)
    # Persist the rename as well as its contents across an abrupt power cut.
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)

def load(path):
    try:return json.loads(path.read_text())
    except (OSError,ValueError):return {}

def power_flags(raw):
    match=re.search(r'throttled=(0x[0-9a-fA-F]+)',raw)
    value=int(match.group(1),16) if match else None
    names={0:'undervoltage_now',1:'frequency_capped_now',2:'throttled_now',3:'temperature_limit_now',
           16:'undervoltage_since_boot',17:'frequency_capped_since_boot',18:'throttled_since_boot',19:'temperature_limit_since_boot'}
    return {'raw':raw,'flags':{name:bool(value & (1<<bit)) for bit,name in names.items()} if value is not None else {}}

def snapshot():
    mem={}
    for line in read('/proc/meminfo').splitlines():
        parts=line.split()
        if parts[0] in ('MemTotal:','MemAvailable:','SwapTotal:','SwapFree:'):mem[parts[0][:-1]]=int(parts[1])
    state=command('systemctl','show',*SERVICES,'-p','Id','-p','ActiveState','-p','SubState','-p','NRestarts','-p','Result','-p','MainPID')
    services=[]
    for block in state.split('\n\n'):
        fields=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
        if fields:services.append(fields)
    temp=read('/sys/class/thermal/thermal_zone0/temp')
    return {'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'boot_id':read('/proc/sys/kernel/random/boot_id'),'uptime_s':float(read('/proc/uptime','0').split()[0]),
            'power':power_flags(command('vcgencmd','get_throttled',timeout=3)),
            'temperature_c':round(float(temp)/1000,1) if temp else None,
            'memory_kib':mem,'load':read('/proc/loadavg'),'services':services,
            'links':{name:{'state':read('/sys/class/net/'+name+'/operstate'),
                           'carrier':read('/sys/class/net/'+name+'/carrier')}
                     for name in ('eth0','usb0')},
            'usb_gadget':{p.name:read(p/'state') for p in Path('/sys/class/udc').glob('*')},
            'pressure':{name:read('/proc/pressure/'+name) for name in ('cpu','memory','io')},
            # The monitor's own / is intentionally read-only under systemd
            # hardening. Read PID 1's view to diagnose the actual host filesystem.
            'root_filesystem':next((line.split()[5] for line in read('/proc/1/mountinfo').splitlines() if line.split()[4]=='/'),'unavailable'),
            # Avoid waking systemd-timedated every sample on this offline Pi.
            'time_synchronized':'yes' if Path('/run/systemd/timesync/synchronized').exists() else 'not confirmed'}

def boot_assessment(previous,current):
    if not previous:return 'First monitored boot; earlier shutdown evidence is unavailable.'
    if previous.get('boot_id')==current['boot_id']:return 'Diagnostics service restarted within the same boot.'
    if previous.get('exit_reason')=='system_shutdown':return 'Previous boot recorded an orderly shutdown request.'
    return 'Previous boot ended without an orderly shutdown record. Power loss, reset, or a hang is possible; cause is unconfirmed.'

def append_sample(sample):
    path=DATA/'health.jsonl'
    if path.exists() and path.stat().st_size>=LIMIT:os.replace(path,DATA/'health.previous.jsonl')
    fd=os.open(path,os.O_WRONLY|os.O_APPEND|os.O_CREAT,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write(json.dumps(sample,separators=(',',':'))+'\n');stream.flush();os.fsync(stream.fileno())
    atomic_json(DATA/'last-state.json',sample)

def report():
    current=snapshot()
    result={'current':current,'last_boot':load(DATA/'last-boot.json'),
            'boot_history':command('journalctl','--list-boots','--no-pager'),
            'kernel_warnings':command('journalctl','-k','-b','-p','warning','-n','120','--no-pager'),
            'previous_boot_tail':command('journalctl','-b','-1','-n','100','--no-pager'),
            'service_events':command('journalctl','-b',*[arg for unit in SERVICES for arg in ('-u',unit)],'-n','150','--no-pager'),
            'kernel_crash_records':{str(p):read(p)[-24000:] for root in ('/sys/fs/pstore','/var/lib/systemd/pstore') for p in Path(root).glob('*') if p.is_file()},
            'limits':'Journal: 128 MiB maximum target, 14 days. Health: two 2 MiB files. Last 10 reports. Abrupt power loss can lose the final unsaved events.'}
    reports=DATA/'reports';reports.mkdir(mode=0o700,parents=True,exist_ok=True)
    name='report-'+current['boot_id'][:8]+'-'+str(int(current['uptime_s']))+'.json'
    path=reports/name
    atomic_json(path,result);atomic_json(DATA/'latest-report.json',result)
    for old in sorted(reports.glob('report-*.json'),key=lambda p:p.stat().st_mtime,reverse=True)[10:]:old.unlink()
    return path,result

def brief(data):
    s=data.get('current',data)
    power=s.get('power',{})
    flags=[name.replace('_',' ') for name,active in power.get('flags',{}).items() if active]
    return [f"CPU: {s.get('temperature_c')} C | uptime {int(s.get('uptime_s',0)//60)} min",
            'Power: '+(', '.join(flags) if flags else power.get('raw','unavailable')),
            'RAM available: '+str(s.get('memory_kib',{}).get('MemAvailable',0)//1024)+' MiB',
            *[x.get('Id','?').replace('.service','')+': '+x.get('ActiveState','?')+'; restarts '+x.get('NRestarts','?') for x in s.get('services',[])],
            'USB: '+str(s.get('usb_gadget',{})),
            data.get('last_boot',{}).get('assessment',''),
            'Report: /var/lib/taccomms-diagnostics/latest-report.json']

def monitor():
    DATA.mkdir(mode=0o700,parents=True,exist_ok=True)
    stop=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    previous=load(DATA/'last-state.json');current=snapshot()
    existing=load(DATA/'last-boot.json')
    if existing.get('boot_id')!=current['boot_id']:
        atomic_json(DATA/'last-boot.json',{'boot_id':current['boot_id'],'assessment':boot_assessment(previous,current),'previous_last_state':previous})
    append_sample(current)
    report()
    print('TacComms persistent diagnostics active; sampling every 30 seconds.',flush=True)
    last=current
    while not stop.wait(30):
        current=snapshot();append_sample(current)
        if current['power']!=last['power'] or current['services']!=last['services']:
            report();print('Power or service state changed; diagnostic report saved.',flush=True)
        last=current
    current=snapshot()
    current['exit_reason']='system_shutdown' if command('systemctl','is-system-running')=='stopping' else 'monitor_stopped'
    append_sample(current)

if __name__=='__main__':
    os.umask(0o077)
    parser=argparse.ArgumentParser();parser.add_argument('--monitor',action='store_true');parser.add_argument('--brief',action='store_true')
    args=parser.parse_args()
    if args.monitor:monitor()
    elif args.brief:print('\n'.join(brief(snapshot())))
    else:
        path,result=report();print('\n'.join(brief(result)));print('Saved: '+str(path))
