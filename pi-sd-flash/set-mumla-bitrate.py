import importlib.util,re
from pathlib import Path
spec=importlib.util.spec_from_file_location('p',Path(__file__).with_name('android-phone.py'))
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
tree=p.ui()
assert any(n.get('text')=='Microphone input quality' for n in tree.iter('node'))
slider=next(n for n in tree.iter('node') if n.get('resource-id')=='se.lublin.mumla:id/seek_bar')
x1,y1,x2,y2=map(int,re.findall(r'\d+',slider.get('bounds')))
lo,hi=x1,x2-1
for _ in range(11):
    value=next(n.get('text') for n in tree.iter('node') if n.get('resource-id')=='se.lublin.mumla:id/seek_bar_value_view')
    number=int(value.split()[0])
    if number==24000:
        p.tap_id('android:id/button1')
        p.tap_attribute('text','Microphone input quality')
        final=next(n.get('text') for n in p.ui().iter('node') if n.get('resource-id')=='se.lublin.mumla:id/seek_bar_value_view')
        assert final=='24000 bps',final
        p.tap_id('android:id/button2')
        print('Saved and reopened: 24000 bps.')
        break
    x=(lo+hi)//2
    p.adb('shell','input','tap',str(x),str((y1+y2)//2))
    tree=p.ui()
    actual=int(next(n.get('text') for n in tree.iter('node') if n.get('resource-id')=='se.lublin.mumla:id/seek_bar_value_view').split()[0])
    if actual<24000:lo=x+1
    elif actual>24000:hi=x-1
else:
    p.tap_id('android:id/button2')
    raise RuntimeError('Exact bitrate not reached; unsaved adjustment cancelled.')
