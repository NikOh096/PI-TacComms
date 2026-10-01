# Another Android phone on the existing TacComms network

- [ ] Install [Mumla](https://mumla-app.gitlab.io/) while internet is available.
- [ ] Pair the headset to the phone and enable call audio.
- [ ] Power the Pi and TC-HTRT01; keep their Ethernet cable connected.
- [ ] Power one configured HD01 using a supported phone USB-C power connection
  or an external USB supply.
- [ ] Join `TC-HTHD01` or `TC-HTHD02` in phone Wi-Fi settings with the existing
  Heltec Wi-Fi password (obtain privately from the owner).
- [ ] Accept “Stay connected” when Android reports no internet. Leave DHCP
  automatic and **leave mobile data enabled**.
- [ ] Add Mumla server `TacComms`, address `10.42.0.137`, port `64738`, a unique
  username, and the existing Mumble participant password. This password differs
  from the Heltec Wi-Fi password. Give each phone its own client certificate.
- [ ] Allow microphone/notification permissions. Verify the Pi certificate on
  first connection against a trusted existing phone or the handoff fingerprint.
- [ ] Set push-to-talk, 24,000 bps, automatic reconnect on, Only TCP off, Tor off.
- [ ] Allow Mumla background activity/unrestricted battery usage if offered.
- [ ] Join the same channel as the other phone. Hold PTT to talk, release to listen.
- [ ] Test speech in both directions, headset microphone routing, and reception
  after locking the phone. Do not assume a headset hardware button controls PTT.

No PC, developer mode, file-transfer mode, or PC Bluetooth pairing is needed.
The phone's local Wi-Fi carries voice to its HD01; HaLow carries it to the gateway.
If login fails, check Wi-Fi attachment, gateway/Pi power and Ethernet, server
address, and the separate Mumble password. A lone participant receives no echo.

A factory-default additional HD01 needs separate US-region HaLow station/bridge
configuration and a unique name before this checklist applies. Existing nodes
do not need resetting or re-pairing for another phone.
