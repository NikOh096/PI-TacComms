"""Apply the small, version-checked TacComms adaptation after Debian patches."""
import shutil
import sys
from pathlib import Path

base=Path(__file__).resolve().parent
source=Path(sys.argv[1]).resolve()
assert '1.5.735-5+deb13u1' in (source/'debian/changelog').read_text().splitlines()[0]

def replace(relative,old,new):
    path=source/relative
    content=path.read_text()
    if new in content:
        return
    assert content.count(old)==1, 'Source anchor changed: '+relative
    path.write_text(content.replace(old,new))

for name in ('TacCommsDenoiser.h','TacCommsDenoiser.cpp','test-filter.cpp'):
    shutil.copyfile(base/name,source/'src/murmur'/name)
replace('src/murmur/ServerUser.h','#include "User.h"',
        '#include "User.h"\n#include "TacCommsDenoiser.h"')
replace('src/murmur/ServerUser.h','\tBandwidthRecord bwr;',
        '\tBandwidthRecord bwr;\n\tTacCommsDenoiser tacCommsDenoiser;')
replace('src/murmur/Server.cpp','\tbuffer.preprocessBuffer();', '''\tbuffer.preprocessBuffer();

    // Every transport shares this path, after Mumble's authentication, mute,
    // bandwidth and recipient/ACL decisions. Preserve all speaker metadata.
    std::array<unsigned char, 1275> tacCommsPacket{};
    if (audioData.usedCodec == Mumble::Protocol::AudioCodec::Opus) {
        const auto filtered = u->tacCommsDenoiser.process(
            audioData.payload.data(), audioData.payload.size(), audioData.frameNumber,
            tacCommsNoiseEnabled(), tacCommsPacket.data(), tacCommsPacket.size());
        if (filtered.action == TacCommsDenoiser::Action::Drop) return;
        if (filtered.action == TacCommsDenoiser::Action::Filtered) {
            audioData.payload = gsl::span<const Mumble::Protocol::byte>(
                tacCommsPacket.data(), static_cast<std::size_t>(filtered.bytes));
        }
    }
''')
replace('src/murmur/CMakeLists.txt','target_link_libraries(mumble-server PRIVATE shared Qt5::Sql)',
'''target_link_libraries(mumble-server PRIVATE shared Qt5::Sql)

# Use the exact noise-reduction implementation bundled with this Mumble source.
set(RENAMENOISE_DEMO_EXECUTABLE OFF)
set(RENAMENOISE_BENCHMARK_EXECUTABLE OFF)
add_subdirectory("${3RDPARTY_DIR}/renamenoise" "taccomms-renamenoise")
find_package(PkgConfig REQUIRED)
pkg_check_modules(TACCOMMS_OPUS REQUIRED IMPORTED_TARGET opus)
target_sources(mumble-server PRIVATE TacCommsDenoiser.cpp TacCommsDenoiser.h)
target_link_libraries(mumble-server PRIVATE renamenoise PkgConfig::TACCOMMS_OPUS m)
add_executable(taccomms-filter-test test-filter.cpp TacCommsDenoiser.cpp)
target_link_libraries(taccomms-filter-test PRIVATE renamenoise PkgConfig::TACCOMMS_OPUS m)
''')
replace('src/murmur/CMakeLists.txt',
        'target_link_libraries(taccomms-filter-test PRIVATE renamenoise PkgConfig::TACCOMMS_OPUS m)',
        '''target_link_libraries(taccomms-filter-test PRIVATE renamenoise PkgConfig::TACCOMMS_OPUS m)

# Select the separately pinned modern model for the TacComms voice path.
include("'''+base.as_posix()+'''/modern-rnnoise.cmake")
target_compile_definitions(mumble-server PRIVATE TACCOMMS_MODERN_RNNOISE)
target_compile_definitions(taccomms-filter-test PRIVATE TACCOMMS_MODERN_RNNOISE)
target_link_libraries(mumble-server PRIVATE taccomms-rnnoise)
target_link_libraries(taccomms-filter-test PRIVATE taccomms-rnnoise)
''')
print('Applied TacComms per-user Opus filter to Debian 1.5.735-5+deb13u1 sources.')
