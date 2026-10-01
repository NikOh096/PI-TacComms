"""Get dependency URLs and signed-index SHA256 values from the Pi's APT cache."""
import json,re,subprocess
packages=['cmake','ninja-build','libboost-dev','libcap-dev','libopus-dev',
          'libprotobuf-dev','protobuf-compiler','libssl-dev','libzeroc-ice-dev',
          'zeroc-ice-compilers','qtbase5-dev','libavahi-compat-libdnssd-dev',
          'nlohmann-json3-dev','dpkg-dev','patch']
text=subprocess.check_output(['apt-get','--print-uris','-y','--no-install-recommends',
    '--no-remove','--no-upgrade','install',*packages],text=True)
result=[]
for line in text.splitlines():
    m=re.fullmatch(r"'([^']+)' (\S+) (\d+) (\S+)",line)
    if not m:continue
    url,name,size,_=m.groups()
    package=name.split('_')[0]
    records=subprocess.check_output(['apt-cache','show',package],text=True)
    matching=[]
    from urllib.parse import unquote
    for paragraph in records.split('\n\n'):
        fields=dict(row.split(': ',1) for row in paragraph.splitlines() if ': ' in row and not row.startswith(' '))
        if fields.get('Filename') and unquote(url).endswith(fields['Filename']):matching.append(fields)
    assert len(matching)==1,(package,len(matching))
    row=matching[0]
    assert 'SHA256' in row
    result.append({'url':url.replace('http://','https://',1),'filename':name,'size':int(size),'sha256':row['SHA256']})
print(json.dumps(result,indent=2))
