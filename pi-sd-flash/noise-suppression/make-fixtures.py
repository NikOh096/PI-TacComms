"""Synthetic speech + impulse fixtures; no recordings or live microphone access."""
import array,json,math,random,sys,wave
from pathlib import Path
base=Path(__file__).resolve().parent
with wave.open(str(base/'speech-clean.wav'),'rb') as wav:
    assert (wav.getnchannels(),wav.getsampwidth(),wav.getframerate())==(1,2,48000)
    pcm=array.array('h',wav.readframes(wav.getnframes()))
if sys.byteorder!='little':pcm.byteswap()
scale=0.16/max(abs(v/32768.0) for v in pcm)
clean=[v/32768.0*scale for v in pcm]
clean += [0.0]*int(0.3*48000)
clean += [0.0]*((-len(clean))%960)
rng=random.Random(29482)
impulses=[0.0]*len(clean)
times=[1.9,3.2,5.0,6.4,8.9,10.8]
for second in times:
    start=int(second*48000)
    for j in range(int(0.12*48000)):
        if start+j>=len(impulses):break
        t=j/48000.0
        impulses[start+j]+=math.exp(-t/0.012)*(0.78*rng.uniform(-1,1)+0.22*math.sin(2*math.pi*110*t))
noise=[rng.uniform(-0.006,0.006) for _ in clean]
clips={}
for name,values in [('clean',clean),('impulses',[a+b+c for a,b,c in zip(clean,impulses,noise)]),
                    ('clipped-impulses',[a+4*b+c for a,b,c in zip(clean,impulses,noise)])]:
    clips[name]=sum(abs(x)>=1 for x in values)
    data=array.array('h',(round(max(-1,min(0.999969,x))*32768) for x in values))
    if sys.byteorder!='little':data.byteswap()
    (base/(name+'.pcm')).write_bytes(data.tobytes())
    with wave.open(str(base/(name+'.wav')),'wb') as out:
        out.setparams((1,2,48000,0,'NONE','not compressed'));out.writeframes(data.tobytes())
report={'synthetic':True,'duration_seconds':len(clean)/48000,'impulse_times':times,
        'clipped_samples':clips,'live_range_test':False}
(base/'fixtures.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
