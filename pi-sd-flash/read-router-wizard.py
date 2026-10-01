import re,urllib.request
for path in ('view/morse/wizard.js','tools/morse/wizard.js','tools/widgets.js'):
    try:
        with urllib.request.urlopen('http://10.42.0.1/luci-static/resources/'+path,timeout=10) as r:text=r.read().decode()
        print('\nRESOURCE:',path,'LENGTH:',len(text),'HEAD:',text[:500])
        matches=list(re.finditer(r'frequency|bandwidth|htmode|s1g|country|call[A-Z]\w+',text,re.I))
        excerpts=[]
        for match in matches:
            excerpt=text[max(0,match.start()-100):match.start()+180]
            if excerpt not in excerpts:excerpts.append(excerpt)
        print('\n'.join(excerpts[:45]))
    except Exception as exc:print(path,type(exc).__name__)
