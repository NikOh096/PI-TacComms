# Third-party components

The repository's original GPL-3.0 `LICENSE` is retained. It does not replace
licenses attached to third-party source or device firmware.

- `pi-sd-flash/taccomms-admin/MumbleServer.ice` is the Mumble project's interface,
  with its original copyright header. See `third-party-licenses/Mumble-LICENSE`.
  Source: https://github.com/mumble-voip/mumble ; Debian source version
  1.5.735-5+deb13u1 is pinned in the audio build.
- RNNoise source and model are downloaded separately from Xiph. Revision and
  SHA-256 hashes are recorded in `upstream-artifacts.json`; license is preserved
  in `third-party-licenses/RNNoise-COPYING` and in downloaded source.
- Opus 1.5.2 is downloaded separately from Xiph. Its license is preserved in
  `third-party-licenses/Opus-COPYING` and in downloaded source.
- `touchscreen-fix/bw-ads7846.dtbo` is the existing third-party ADS7846 overlay
  used on this Pi, retained as a hardware setup artifact. The local development
  record did not preserve a complete upstream license/provenance record for
  this binary; verify that separately before redistributing a product image.
- `noise-suppression/speech-clean.wav` is the synthetic speech seed used for
  the existing synthetic tests, not a microphone recording. Generated noisy and
  filtered audio, dependency packages and model weights are excluded from Git.

Raspberry Pi OS, Heltec firmware, Android tools, and system packages are not
redistributed here. Original package URLs/hashes remain in package manifests.
