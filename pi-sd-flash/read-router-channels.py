import re,urllib.request
for path in ('halow.js','tools/widgets.js'):
    with urllib.request.urlopen('http://10.42.0.1/luci-static/resources/'+path,timeout=10) as r:text=r.read().decode()
    print('RESOURCE',path)
    if path=='halow.js':print(text[:9000])
    else:
        for term in ('write:function','cfgvalue:function','loadChannelMap','s1g_prim_chwidth','s1g_prim_1mhz_chan_index'):
            index=text.find(term)
            if index>=0:print(text[max(0,index-60):index+1400])
