import importlib.util
from pathlib import Path
spec=importlib.util.spec_from_file_location('b',Path(__file__).with_name('phone-browser.py'))
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
print(b.evaluate('''(async()=>{try{const r=await fetch('/ubus',{signal:AbortSignal.timeout(6000)});return {status:r.status,text:(await r.text()).slice(0,200)}}catch(e){return {name:e.name,message:e.message}}})()'''))
