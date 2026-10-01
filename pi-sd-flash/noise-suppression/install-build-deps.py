import os,subprocess
packages=['cmake','ninja-build','libboost-dev','libcap-dev','libopus-dev',
          'libprotobuf-dev','protobuf-compiler','libssl-dev','libzeroc-ice-dev',
          'zeroc-ice-compilers','qtbase5-dev','libavahi-compat-libdnssd-dev',
          'nlohmann-json3-dev','dpkg-dev','patch']
env=dict(os.environ,DEBIAN_FRONTEND='noninteractive')
raise SystemExit(subprocess.run(['apt-get','install','-y','--no-install-recommends',
    '--no-remove','--no-upgrade','-o','Acquire::Retries=0',
    '-o','Acquire::http::Timeout=15','-o','Acquire::https::Timeout=15',*packages],env=env).returncode)
