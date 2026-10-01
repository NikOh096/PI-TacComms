gateway=login('10.42.0.1',PASSWORD)
assert rpc('10.42.0.1',gateway,'system','board',{})['model']=='Heltec HT-H7608-V2'
deadline=time.monotonic()+80
while time.monotonic()<deadline:
    time.sleep(2)
    try:
        leases=rpc('10.42.0.1',gateway,'luci-rpc','getDHCPLeases',{})['dhcp_leases']
        matches=[v for v in leases if v.get('hostname','').lower() in (OLD_NAME.lower(),NEW_NAME.lower())
                 or v.get('macaddr','').lower().endswith(MAC_SUFFIX)]
        if not matches:continue
        address=matches[0]['ipaddr']
        board=rpc(address,SESSION,'system','board',{})
        assert board.get('model')=='Heltec HT-HD01-V2'
        network=rpc(address,SESSION,'uci','get',{'config':'network'})['values']
        wireless=rpc(address,SESSION,'uci','get',{'config':'wireless'})['values']
        dhcp=rpc(address,SESSION,'uci','get',{'config':'dhcp'})['values']
        system=rpc(address,SESSION,'uci','get',{'config':'system'})['values']
        assert network['lan']['proto']=='dhcp'
        assert wireless['default_radio1']['mode']=='sta' and wireless['default_radio1']['network']=='lan'
        assert wireless['default_radio1']['ssid']=='TC-HTRT01' and wireless['default_radio1']['key']==PASSWORD
        assert wireless['default_radio0']['ssid']==NEW_NAME and wireless['default_radio0']['key']==PASSWORD
        assert dhcp['lan']['ignore']=='1'
        assert any(v.get('hostname')==NEW_NAME for v in system.values())
        rpc(address,SESSION,'uci','confirm',{})
        print('CONFIRMED:',NEW_NAME,'connected over HaLow; management address:',address,flush=True)
        fresh=set_admin_password(address,SESSION)
        assert rpc(address,fresh,'system','board',{})['model']=='Heltec HT-HD01-V2'
        record={'name':NEW_NAME,'previous_name':OLD_NAME,'ip':address,'mac':matches[0].get('macaddr'),
                'bridge_verified':True,'admin_password_updated':True,'time':time.time()}
        Path('/var/lib/taccomms/'+NEW_NAME.lower()+'.json').write_text(json.dumps(record,indent=2))
        print('PAIRING_RESULT='+json.dumps(record),flush=True)
        break
    except (OSError,RuntimeError,KeyError):continue
else:raise RuntimeError('HD01 not verified. Automatic rollback remains armed; no confirmation sent.')
