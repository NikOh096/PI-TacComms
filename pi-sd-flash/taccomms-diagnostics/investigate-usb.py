import json,re,subprocess
from pathlib import Path

def run(*args):
    r=subprocess.run(args,capture_output=True,text=True,timeout=20)
    return (r.stdout+r.stderr).strip()

base=Path('/var/lib/taccomms-diagnostics')
print('BOOTS:',run('journalctl','--list-boots','--no-pager'))
print('LAST BOOT:',(base/'last-boot.json').read_text() if (base/'last-boot.json').exists() else 'unavailable')
pattern=re.compile(r'under.?voltage|voltage normal|thrott|over.?current|dwc2.*(reset|disconnect|error|timeout)|usb0|panic|out of memory|oom.kill|mmc.*(error|timeout)|EXT4-fs error',re.I)
for boot in ('-1','0'):
    raw=run('journalctl','-k','-b',boot,'--no-pager','-o','json')
    events=[]
    for line in raw.splitlines():
        try:item=json.loads(line)
        except ValueError:continue
        message=item.get('MESSAGE','')
        if pattern.search(message):events.append({'uptime_s':int(item.get('__MONOTONIC_TIMESTAMP','0'))/1000000,'message':message})
    print('KERNEL EVENTS BOOT '+boot+':',json.dumps(events[-70:]))
print('PREVIOUS BOOT END:',run('journalctl','-b','-1','--no-pager','-n','35','-o','short-monotonic'))
samples=[]
for path in (base/'health.previous.jsonl',base/'health.jsonl'):
    if path.exists():
        for line in path.read_text().splitlines():
            try:samples.append(json.loads(line))
            except ValueError:pass
changes=[];last=None
for sample in samples:
    state=(sample.get('boot_id'),sample.get('power',{}).get('raw'),sample.get('usb_gadget'))
    if state!=last:
        changes.append({'uptime_s':sample.get('uptime_s'),'boot_id':sample.get('boot_id'),'power':sample.get('power',{}).get('raw'),'usb':sample.get('usb_gadget')})
        last=state
print('HEALTH TRANSITIONS:',json.dumps(changes[-45:]))
if samples:
    latest=samples[-1]
    print('LATEST:',json.dumps({key:latest.get(key) for key in ('utc','boot_id','uptime_s','power','temperature_c','memory_kib','services','links','usb_gadget')}))
