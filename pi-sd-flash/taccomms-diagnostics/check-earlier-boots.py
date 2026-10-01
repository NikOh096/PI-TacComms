import json,re,subprocess
def run(*args):return subprocess.run(args,capture_output=True,text=True,timeout=15).stdout
pattern=re.compile(r'under.?voltage|voltage normal|panic|out of memory|oom.kill|watchdog.*(reset|lockup)|mmc.*(error|timeout)|EXT4-fs error|shutdown|rebooting',re.I)
for boot in ('-7','-6','-5','-4','-3','-2','-1','0'):
    rows=[]
    for line in run('journalctl','-b',boot,'-k','-o','json','--no-pager').splitlines():
        try:item=json.loads(line)
        except ValueError:continue
        msg=item.get('MESSAGE','')
        if pattern.search(msg):rows.append({'uptime_s':int(item.get('__MONOTONIC_TIMESTAMP','0'))/1e6,'message':msg})
    print(json.dumps({'boot':boot,'kernel_findings':rows,'final_entries':run('journalctl','-b',boot,'-n','3','-o','short-monotonic','--no-pager').strip()}))
