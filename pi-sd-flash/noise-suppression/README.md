# TacComms central voice filtering

The implementation is under validation; this file is not proof of installation.
The installed version, once deployed, is recorded on the Pi at
`/usr/local/lib/taccomms-noise/build-info.json`.

Each speaker has a separate Opus decoder, RNNoise state, peak limiter and Opus
encoder. Filtering is inserted in Mumble's shared UDP/TCP forwarding path after
authentication, mute, bandwidth and recipient decisions. Speaker identity,
channel routing, positional metadata and end-of-talk flags are retained.
No audio is recorded by the live filter.

The supported path is mono Opus in 10, 20, 40 or 60 ms packets. Output is 24 kbit/s
Opus voice. Other codecs, stereo and unsupported packet durations pass through.
Missing/invalid mode configuration disables the filter. An administrator can
switch it off without dropping calls. A lightweight peak limiter remains in
the supported path if sustained CPU overload temporarily bypasses RNNoise.
The limiter operates before encoding, with a -12 dBFS ceiling, instantaneous
attack and 50 ms release; it does not define a calibrated headphone output level.

The model is Xiph RNNoise revision
`70f1d256acd4b34a572f999a05c87bf00b67730d`; the upstream model archive SHA-256 is
`0a8755f8e2d834eff6a54714ecc7d75f9932e845df35f8b59bc52a7cfe6e8b37`.
The older ReNameNoise model bundled with Mumble was evaluated and rejected for
this implementation after substantially weaker synthetic-noise suppression.
Upstream source and license files are retained under `inspect/`.

Windows synthetic-fixture results (not headset/range validation):

| Fixture | Original Opus STOI | Filtered STOI | Original ESTOI | Filtered ESTOI |
|---|---:|---:|---:|---:|
| Speech plus six unclipped impulses | 0.921 | 0.963 | 0.865 | 0.904 |
| Speech plus clipped impulses | 0.888 | 0.960 | 0.851 | 0.901 |

These scores measure a synthetic voice and generated impulse mixture. They are
not percentages of words understood and do not guarantee performance with an
actual microphone. Alignment measured about 26 ms additional signal delay over
the original encoded path. Clean filtered speech scored STOI 0.976. The complete
measurements and audio examples are in `fixture-results.json` and the matching
WAV files. The truncated end of a transmission and real headset overload still
need listening tests; microphone clipping cannot be reconstructed exactly.

Validation consists of core packet/reset/isolation checks, sustained four-active
speaker processing, and an isolated Mumble server with encrypted UDP and TCP
voice, password rejection, mute, channel isolation, end flags and bypass checks.
The isolated server uses a separate loopback port and temporary database.

Deployment retains `/usr/bin/mumble-server`, backs up the live configuration and
database, and uses a systemd override to select the custom binary. Installation
requires the test reports to pass and the live server to be idle. Startup failure
restores the original service and backend. After deployment, use `help audio`,
`noise status`, `noise on` or `noise off` in the PIN-protected console.
