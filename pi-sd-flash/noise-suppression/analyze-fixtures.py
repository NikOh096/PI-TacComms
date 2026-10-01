"""Aligned synthetic-fixture comparisons. These are not live range validation."""
import json,sys,wave
from pathlib import Path
base=Path(__file__).resolve().parent
sys.path.insert(0,str(base/'analysis-tools'))
import numpy as np
from scipy import signal
from pystoi import stoi

rate=48000
reference=np.fromfile(base/'clean.pcm',dtype='<i2').astype(float)/32768
fixtures=json.loads((base/'fixtures.json').read_text())
report={'synthetic_only':True,'live_headset_validation':False,'outputs':{}}
for path in sorted(base.glob('*-baseline.pcm'))+sorted(base.glob('*-filtered.pcm')):
    audio=np.fromfile(path,dtype='<i2').astype(float)/32768
    if len(audio)!=len(reference):
        continue
    # Find only plausible positive codec/filter delay, not an arbitrary large lag.
    corr=signal.correlate(audio,reference,mode='full',method='fft')
    center=len(reference)-1
    lag=int(np.argmax(corr[center:center+rate//5]))
    a=reference[:len(audio)-lag] if lag else reference
    b=audio[lag:]
    score=float(stoi(a,b,rate,extended=False))
    extended=float(stoi(a,b,rate,extended=True))
    transient=np.zeros(len(a),dtype=bool)
    for second in fixtures['impulse_times']:
        transient[int(second*rate):min(len(a),int((second+.15)*rate))]=True
    speech=np.abs(a)>.005
    ordinary=speech & ~transient
    gain=float(np.dot(a[ordinary],b[ordinary])/max(np.dot(a[ordinary],a[ordinary]),1e-12))
    item={'delay_ms':lag*1000/rate,'stoi':score,'estoi':extended,
          'peak_dbfs':float(20*np.log10(max(np.max(np.abs(b)),1e-9))),
          'transient_rms_dbfs':float(10*np.log10(np.mean(b[transient]**2)+1e-18)),
          'speech_gain_db':float(20*np.log10(max(abs(gain),1e-9)))}
    report['outputs'][path.stem]=item
    with wave.open(str(path.with_suffix('.wav')),'wb') as out:
        out.setparams((1,2,rate,0,'NONE','not compressed'));out.writeframes(path.read_bytes())
(base/'fixture-results.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
