import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('b',Path(__file__).with_name('phone-browser.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
host=sys.argv[1]
assert host in ('10.42.0.1','192.168.100.1')
print(b.evaluate('location.assign('+json.dumps('http://'+host+'/cgi-bin/luci/')+'); true'))
