# Build handoff, 2026-09-29

Production Mumble remains the original Debian server. Do not report central
filtering installed. Persistent diagnostics and the screen startup fix ARE live.
The Pi USB adapter disappeared again while compiling ServerUser.cpp; retrieve
the newest diagnostics before continuing a build. The previous boot ID was
`f8164a34-5112-4f89-aed5-237b372b2c42`.

The modern model successfully compiled after conversion warnings were disabled
only for generated `rnnoise_data.c`; GCC otherwise spent over ten minutes on its
78 MB of decimal initializers. This changes diagnostics, not model values.
Build session 96953 ended on connection reset after step 23/42. It was using
one worker. No deployment was attempted.

On the PC: core/reset/malformed-packet tests pass. The 20-second four-active
speaker test passed, mean processing 2.32 ms per 20 ms packet, no neural fallback.
Synthetic speech/impulse comparisons are in `fixture-results.json`. Pi performance
and live server integration are still unverified.

Next steps:

1. Retrieve `/var/lib/taccomms-diagnostics/latest-report.json`, health history,
   and previous boot journal. Determine whether the last disconnect was an
   intentional power cycle, a whole-system reset, or only USB.
2. Sync the latest `TacCommsDenoiser.cpp` before resuming: the PC added Drop on
   non-finite filter output / encode failure after the last source sync.
   The latest `modern-inputs.tar.gz` contains all current sources and hashes.
3. Resume `build.py` as niko. Do not install before `run-pi-tests.py` passes core,
   four-active-speaker load, and isolated encrypted UDP/TCP integration checks.
4. `test-integration.py` and `noise_control.py` have been staged on the Pi.
   `install-filter.py` is prepared but has never run; it requires the test
   receipts, an idle live server, and retains the original binary for rollback.
   Review any test failures and the untested installation before using it.
5. Enable the mode-file path through the systemd environment, as prepared in
   the installer. Admin needs its narrowly scoped ReadWritePaths audio directory.
6. Verify production login/UDP, actual binary, filter mode, diagnostics, PIN
   enforcement, and service stability after deployment. A real headset test
   remains necessary; do not substitute synthetic scores for that check.

The phone is absent from ADB. Restore its temporary stay-awake setting from 15
to its original 0 when it reconnects. The Pi's Ethernet carrier was down; the
user has been asked to check its cable to TC-HTRT01.
