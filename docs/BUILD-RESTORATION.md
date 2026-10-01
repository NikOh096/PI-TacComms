# Restore audio build inputs on another machine

The normal Mumble service is working. These steps restore the unfinished central
filter development environment; they do not replace production Mumble.

## Source archives

Python 3.12+ is required for safe tar extraction. From the repository root:

```sh
python pi-sd-flash/noise-suppression/fetch-upstream.py --extract
```

This downloads five pinned source/model archives, verifies their lengths and
SHA-256 hashes, and extracts sources to ignored `noise-suppression/inspect/`.
It runs no downloaded code and refuses to overwrite an existing inspect tree.
`--cache /path/to/old/noise-suppression` can reuse the old archives. Combine
`--cache` with `--verify-only` to check existing archives without copying them.

The exact Debian revision is required by `patch-source.py`; do not substitute
a newer Mumble release without reviewing and adapting the patch. If an upstream
archive moves, locate that exact hash in the publisher's archives rather than
removing checksum checks. The RNNoise model currently uses a Gentoo distribution
mirror because Xiph's model endpoint had an expired TLS certificate when checked.
The exact original Xiph SHA-256 is still required; TLS checking stays enabled.
`packages.json` holds the Pi build package manifest;
other package manifests preserve base/admin dependencies. Cached .deb files and
package indexes must be downloaded/re-created or transferred separately.

## Windows core checks

Use CMake and a C/C++ compiler. Configure the `noise-suppression` directory to an
ignored build directory, build Release, and run `taccomms-modern-test` there.
The existing `test-filter.cpp` defines core and load-test arguments. The CMake
project also retains the older filter comparison target.

`speech-clean.wav` is the original synthetic speech seed. `make-fixtures.py`
recreates noisy fixtures; `analyze-fixtures.py` needs numpy, scipy and pystoi.
Generated PCM/WAV outputs are ignored. Historical `fixture-results.json` remains
in Git as evidence, not as a claim that the current checkout has been retested
with real equipment.

## Resume on the Pi

Read `pi-sd-flash/noise-suppression/RESUME.md` together with `docs/CURRENT-STATE.md`.
The existing isolated directory is `/home/niko/taccomms-noise-build`. Inspect it
and fresh power/service diagnostics first; do not erase a partly completed build.

After restoring upstream sources, `package-modern.py` regenerates the source
bundle and file hashes from the current local code. Transfer reviewed build/test
sources and the verified original/ Debian-patch archives using the pinned USB
SSH connection. The latest C++ Drop handling must reach the Pi before resuming.
The original `build.py` runs as niko and uses one worker.

`run-pi-tests.py` must pass core, four-active-speaker load, and isolated encrypted
UDP/TCP integration checks before installation. The prepared `install-filter.py`
has not been exercised on this Pi; review it and its rollback behavior first.
It requires matching test evidence and zero connected users. It patches the
current live backend narrowly so diagnostics and PIN behavior remain intact.
Do not stage the whole prototype admin directory over the working installation.

Only a verified `/usr/local/lib/taccomms-noise/build-info.json`, matching running
binary, service/transport checks, and actual listening tests establish deployment.
The original `/usr/bin/mumble-server` remains the fallback.
