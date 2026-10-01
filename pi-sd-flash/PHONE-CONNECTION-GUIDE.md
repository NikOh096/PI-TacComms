# TacComms phone and HaLow network

Updated 2026-09-29. Both HD01 nodes are paired to the H7608. Pixel login as N1K0 through TC-HTHD02 is verified. Through TC-HTHD01, the phone reached the Pi and its matching TLS certificate. A two-phone conversation still needs a test.

| Device | Wi-Fi name and hostname | Reserved address | Original label |
|---|---|---|---|
| H7608 gateway | TC-HTRT01 | 10.42.0.1 | WHL-AP-72AA |
| HD01 node 1 | TC-HTHD01 | 10.42.0.160 | HT-HD01-BFD0; MAC ends BF:D0 |
| HD01 node 2 | TC-HTHD02 | 10.42.0.161 | HT-HD01-A04E; MAC ends A0:4E |
| Raspberry Pi | halow-pi / TacComms | 10.42.0.137 | Ethernet MAC DC:A6:32:B9:EF:13 |

The requested password is applied to ordinary Wi-Fi, HaLow credentials, and administrator logins on all three Heltec devices. Administrator username: root. The password is saved in protected private/tc-network.json. The Mumble server password and Pi touchscreen PINs are unchanged.

## Connect a phone

1. Power the Pi, gateway and the HD01 carried with the phone. Keep Pi Ethernet connected to the gateway.
2. Join TC-HTHD01 or TC-HTHD02 in Android Wi-Fi settings using the new network password.
3. If Android reports no internet, choose stay connected / use this network anyway. This local voice network does not require internet. Switching to home Wi-Fi disconnects the phone from TacComms.
4. In Mumla, open TacComms: address 10.42.0.137, port 64738, username N1K0 on the configured Pixel, and the existing saved Mumble server password. Use a different username on every additional phone.
5. Join the same channel as other participants. Press and hold PUSH-TO-TALK to speak, then release to listen. A lone participant will not hear their own voice echoed back.

Signal path: phone Wi-Fi -> HD01 -> HaLow -> TC-HTRT01 -> Ethernet -> Pi Mumble server. USB cables supply power or setup access; the configured phone-to-HD01 voice path uses Wi-Fi. File-transfer and developer modes are not needed for normal calls.

## Verification

H7608 is the DHCP source and HaLow AP, United States channel 25 / 914.5 MHz / 1 MHz width. Both HD01s are station/client bridges of TC-HTRT01, with their own DHCP servers disabled. Both ordinary hotspots are on the same LAN as the Pi. All three current hostnames, radio names/passwords and fresh administrator logins are verified. Pi and dongles have DHCP reservations.

Mumble login through node 2 is verified. Push-to-talk is enabled, microphone input quality is saved and verified at 24,000 bps, and automatic reconnect is on. Only TCP and Tor are off. The authenticated connection used TCP fallback; UDP voice over HaLow and a two-phone audio conversation have not been verified. At the latest check, the phone had disconnected from Mumble and was absent from PC USB debugging. A fresh phone connection check and restoration of its temporary developer stay-awake setting remain pending.

Pi certificate SHA-256: eb:c5:6e:a5:f4:b1:0b:07:bf:22:c1:f7:b1:da:35:cd:ef:d2:bd:4b:42:2e:3e:7a:25:6b:7b:2b:97:ca:bb:a1.

## Backups

Verified protected PC network backup: private/tc-network-configured-20260929-005114.tar.gz. Original dongle configurations remain under private/. Pi settings, PIN hashes, calibration and Mumble database recovery backup: see recovery-latest.json. The Pi recovered without a reflash.

Official references: [Heltec bridge networking](https://wiki.heltec.org/docs/devices/wifi-halow/ht-hd01/lan), [HD01 AP/client setup](https://wiki.heltec.org/docs/devices/wifi-halow/ht-hd01/ap?ap=sta).
