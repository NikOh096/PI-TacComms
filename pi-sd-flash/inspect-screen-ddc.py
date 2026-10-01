import subprocess
for args in [
 ['id','taccomms'],
 ['runuser','-u','taccomms','--','ddcutil','--bus','20','--skip-ddc-checks','--mccs','2.2','--disable-dynamic-sleep','--sleep-multiplier','2','getvcp','D6'],
 ['systemctl','show','taccomms-screen.service','-p','ExecMainStartTimestamp','-p','SupplementaryGroups'],
 ['journalctl','-u','taccomms-screen.service','--since','15 minutes ago','--no-pager','-o','short-iso']]:
    r=subprocess.run(args,text=True,capture_output=True,timeout=30)
    print('Command:',args[0], 'exit:',r.returncode)
    print(r.stdout[-14000:]+r.stderr[-4000:])
