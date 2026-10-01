import sys
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
from screen import Screen,rgb565
from PIL import Image
assert rgb565(Image.new('RGB',(1,1),'red'))==b'\x00\xf8'
assert rgb565(Image.new('RGB',(1,1),'green'))==b'\x00\x04'
assert rgb565(Image.new('RGB',(1,1),'blue'))==b'\x1f\x00'
screen=Screen(preview=True)
dest=Path('/home/niko/taccomms-stage')
screen.status=['Server    RUNNING','Address   10.42.0.137','Port      64738 TCP/UDP','','Battery   -- (sensor needed)','Power in  disconnected','Pi power  OK','CPU       41 C   Load 0.12','Uptime    1h 24m']
for mode in ('status','enroll','admin','emergency'):
    screen.mode=mode if mode!='enroll' else 'status'
    if mode=='enroll': screen.form_start('enroll')
    if mode=='admin': screen.lines=['help users','users  (live names + speaker activity)','kick SESSION [reason]','ban SESSION [reason]','mute SESSION on|off','deafen SESSION on|off']
    if mode=='emergency': screen.state['emergency']=True
    screen.image().save(dest/(mode+'.png'))
print('Framebuffer packing and preview generation passed.')
