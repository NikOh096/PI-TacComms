host='10.42.0.1'
try:sid=login(host,PASSWORD)
except RuntimeError:sid=login(host,'heltec.org')
board=rpc(host,sid,'system','board',{})
assert board['model']=='Heltec HT-H7608-V2' and board['hostname'] in ('WHL-AP-72AA','TC-HTRT01')
before={n:rpc(host,sid,'uci','get',{'config':n})['values'] for n in ('system','network','wireless','dhcp')}
assert before['network']['lan']['ipaddr']=='10.42.0.1'
backup=save_backup('before-tc-gateway',before)
system=next(k for k,v in before['system'].items() if v.get('.type')=='system')
rpc(host,sid,'uci','set',{'config':'system','section':system,'values':{'hostname':'TC-HTRT01'}})
for section in ('default_radio0','default_radio1'):
    assert before['wireless'][section]['mode']=='ap'
    rpc(host,sid,'uci','set',{'config':'wireless','section':section,'values':{'ssid':'TC-HTRT01','key':PASSWORD}})
rpc(host,sid,'uci','apply',{'timeout':120,'rollback':True})
print('Gateway name and radio passwords applied; verification rollback armed.',flush=True)
deadline=time.monotonic()+65
while time.monotonic()<deadline:
    time.sleep(2)
    try:
        wireless=rpc(host,sid,'uci','get',{'config':'wireless'})['values']
        radio=rpc(host,sid,'luci-rpc','getWirelessDevices',{})
        if not all(radio[n].get('up') and not radio[n].get('pending') for n in ('radio0','radio1')):continue
        assert all(wireless[n]['ssid']=='TC-HTRT01' and wireless[n]['key']==PASSWORD for n in ('default_radio0','default_radio1'))
        assert rpc(host,sid,'uci','get',{'config':'network'})['values']==before['network']
        assert rpc(host,sid,'uci','get',{'config':'system'})['values'][system]['hostname']=='TC-HTRT01'
        rpc(host,sid,'uci','confirm',{})
        print('CONFIRMED: TC-HTRT01 radios active; Ethernet LAN and Pi address preserved.',flush=True)
        break
    except (OSError,RuntimeError):continue
else:raise RuntimeError('Gateway verification failed; automatic rollback remains armed.')
fresh=set_admin_password(host,sid)
print('Gateway identity:',rpc(host,fresh,'system','board',{})['hostname'])
Path('/var/lib/taccomms/tc-gateway.json').write_text(json.dumps({'hostname':'TC-HTRT01','ip':host,'wifi_password_updated':True,'admin_password_updated':True,'time':time.time()}))
