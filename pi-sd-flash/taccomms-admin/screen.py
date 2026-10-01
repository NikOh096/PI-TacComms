#!/usr/bin/python3
"""Framebuffer touchscreen UI; unprivileged client of the local admin service."""
import fcntl
import json
import math
import mmap
import os
from pathlib import Path
import queue
import select
import signal
import struct
import subprocess
import sys
import textwrap
import threading
import time
from PIL import Image, ImageChops, ImageDraw, ImageFont

from client import request, wait_ready
from legacy import Console, command

W,H=640,480
BG='#071219'; PANEL='#132935'; FG='#e1f4f6'; CYAN='#41e4e5'; MUTED='#90aab4'; RED='#ff7373'; GREEN='#74f5a6'
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
CAL=Path('/var/lib/taccomms-ui/touch.json')
EVENT=struct.Struct('qqHHi')


def rgb565(im):
    r,g,b=im.convert('RGB').split()
    low=ImageChops.add(g.point(lambda x:(x&0x1c)<<3),b.point(lambda x:x>>3))
    high=ImageChops.add(r.point(lambda x:x&0xf8),g.point(lambda x:x>>5))
    return Image.merge('LA',(low,high)).tobytes()


class Touch(threading.Thread):
    def __init__(self, events):
        super().__init__(daemon=True)
        self.events=events; self.running=True; self.fd=None

    def run(self):
        while self.running:
            try:
                path=next(p for p in Path('/sys/class/input').glob('event*/device/name') if 'ADS7846' in p.read_text())
                fd=os.open('/dev/input/'+path.parents[1].name,os.O_RDONLY|os.O_NONBLOCK)
                self.fd=fd
                # Monotonic input timestamps are independent of render/RPC delays.
                fcntl.ioctl(fd,0x400445a0,struct.pack('i',1))  # EVIOCSCLOCKID
                fcntl.ioctl(fd,0x40044590,struct.pack('i',1))  # EVIOCGRAB
                x=y=None; down=False; start=None; points=[]; finish=False
                while self.running:
                    if not select.select([fd],[],[],1)[0]: continue
                    raw=os.read(fd,EVENT.size*128)
                    if not raw: raise OSError('touch disconnected')
                    for i in range(0,len(raw)-EVENT.size+1,EVENT.size):
                        sec,usec,kind,code,val=EVENT.unpack_from(raw,i); now=sec+usec/1e6
                        if kind==3 and code==0: x=val
                        if kind==3 and code==1: y=val
                        if kind==1 and code==330:
                            if val==1 and not down:
                                down=True; start=now; points=[]
                                self.events.put(('down',now))
                            elif val==0 and down:
                                finish=True
                        if kind==0 and code==0:
                            if down and not finish and x is not None and y is not None:
                                points.append((x,y))
                            if finish:
                                if points and now-start>=0.008:
                                    # Median avoids spikes on a resistive panel.
                                    xx=sorted(p[0] for p in points)[len(points)//2]
                                    yy=sorted(p[1] for p in points)[len(points)//2]
                                    self.events.put(('tap',start,now,xx,yy))
                                down=False; finish=False; points=[]
            except (OSError,StopIteration):
                self.events.put(('touch_error',))
                time.sleep(1)
            finally:
                if self.fd is not None:
                    os.close(self.fd); self.fd=None


class Screen:
    def __init__(self, preview=False):
        self.preview=preview; self.running=True; self.mode='status'; self.token=''
        self.state={'enrolled':False,'emergency':False}; self.last_touch=time.monotonic()
        self.status=[]; self.lines=['Type help to list commands.']; self.input=''
        self.form=[]; self.form_values=[]; self.form_kind=''; self.form_index=0
        self.message=''; self.message_until=0; self.buttons=[]; self.offset=0
        self.users=[]; self.user_view=False; self.shift=False; self.symbols=False
        self.legacy=Console(); self.events=queue.Queue(); self.page=0
        self.last_state=0; self.last_status=0; self.last_users=0; self.last_render=0
        self.asleep=False; self.waking=False; self.confirm_id=''; self.cal_points=[]
        self.cal_candidate=None; self.cal_last=0
        self.power_probe=None; self.last_power_probe=0
        self.calibration=json.loads(CAL.read_text()) if CAL.exists() else None
        self.fonts={n:ImageFont.truetype(FONT,n) for n in (18,20,22,24,28,32)}
        self.header_font=ImageFont.truetype(FONT.replace('.ttf','-Bold.ttf'),32)

    def say(self,text):
        self.message=str(text); self.message_until=time.monotonic()+8

    def call(self,op,**fields):
        return request(op,token=self.token,**fields)

    def clear_secrets(self):
        self.input=''; self.form_values=[]; self.form=[]; self.form_index=0; self.form_kind=''
        self.confirm_id=''

    def lock(self):
        if self.token:
            try: self.call('logout')
            except Exception: pass
        self.token=''; self.clear_secrets(); self.mode='status'; self.user_view=False
        self.lines=['Type help to list commands.']; self.users=[]; self.offset=0

    def form_start(self,kind):
        self.clear_secrets(); self.form_kind=kind; self.mode='form'
        self.form={
            'enroll':[('admin','New admin PIN'),('admin_confirm','Confirm admin PIN'),('recovery','New recovery PIN'),('recovery_confirm','Confirm recovery PIN')],
            'login':[('pin','Enter admin PIN')], 'recover':[('pin','Emergency recovery PIN')],
            'password':[('new','New server password'),('confirm','Confirm password')],
            'admin':[('new','New admin PIN'),('confirm','Confirm admin PIN')],
            'recovery':[('old','Current recovery PIN'),('new','New recovery PIN'),('confirm','Confirm recovery PIN')]
        }[kind]

    def form_submit(self):
        numeric=self.form_kind!='password'
        if numeric and (len(self.input)!=6 or not self.input.isascii() or not self.input.isdigit()):
            self.say('Enter exactly six digits.'); return
        if not self.input:
            self.say('Enter a value.'); return
        self.form_values.append(self.input); self.input=''; self.form_index+=1
        if self.form_index<len(self.form): return
        kind=self.form_kind; values=dict(zip([x[0] for x in self.form],self.form_values))
        self.form_values=[]
        try:
            if kind=='enroll':
                answer=self.call('enroll',**values); self.lock(); self.state=self.call('state'); self.say('Both PINs saved.')
            elif kind=='login':
                answer=self.call('login',**values); self.token=answer['token']; self.clear_secrets(); self.mode='admin'
            elif kind=='recover':
                self.call('recover',**values); self.lock(); self.state=self.call('state'); self.say('Emergency lock cleared.')
            else:
                answer=self.call('secret',kind=kind,**values); self.clear_secrets(); self.mode='admin'; self.apply(answer)
        except Exception as exc:
            self.form_start(kind); self.say(str(exc))

    def apply(self,answer):
        if answer.get('logout'):
            self.lock(); self.say('Saved. Admin locked.'); return
        if answer.get('emergency'):
            self.lock(); self.state=self.call('state'); self.mode='emergency'; return
        if answer.get('prompt'):
            self.form_start(answer['prompt']); return
        if answer.get('calibrate'):
            self.cal_points=[]; self.cal_candidate=None; self.cal_last=0; self.mode='calibrate'; return
        self.lines=answer.get('lines',[]); self.offset=0
        self.user_view=answer.get('view') in ('users','devices')
        self.users=answer.get('users',[])
        if answer.get('confirm'):
            self.confirm_id=answer['confirm']; self.mode='confirm'
        else: self.mode='admin'

    def execute(self):
        line=self.input.strip(); self.input=''; self.user_view=False
        try: self.apply(self.call('command',line=line))
        except Exception as exc: self.lines=[str(exc)]; self.offset=0

    def emergency(self):
        try:
            self.call('emergency'); self.lock(); self.state=self.call('state'); self.mode='emergency'
        except Exception as exc: self.say(str(exc))

    def position(self,x,y):
        if self.calibration:
            a,b,c,d,e,f=self.calibration
            return max(0,min(W-1,a*x+b*y+c)), max(0,min(H-1,d*x+e*y+f))
        return max(0,min(W-1,(x-240)/(3900-240)*W)), max(0,min(H-1,(3900-y)/(3900-240)*H))

    def calibration_tap(self,x,y):
        if time.monotonic()-self.cal_last<0.65: return
        self.cal_last=time.monotonic()
        if self.cal_candidate is not None:
            a,b,c,d,e,f=self.cal_candidate
            if math.hypot(a*x+b*y+c-510,d*x+e*y+f-355)>40:
                self.cal_points=[]; self.cal_candidate=None
                self.say('Check missed. Tap target centers again.'); return
            self.calibration=self.cal_candidate
            CAL.parent.mkdir(parents=True,exist_ok=True)
            tmp=CAL.with_suffix('.new'); tmp.write_text(json.dumps(self.calibration)); tmp.replace(CAL)
            self.mode='admin' if self.token else 'status'; self.say('Calibrated. Use Admin for PIN access.')
            return
        self.cal_points.append((x,y))
        if len(self.cal_points)<3: return
        # Fit an affine map using three non-collinear targets. This handles axis
        # swaps and inversions without relying on the driver's reversed ranges.
        src=self.cal_points; dst=[(70,80),(570,80),(320,400)]
        x1,y1=src[0]; x2,y2=src[1]; x3,y3=src[2]
        det=x1*(y2-y3)+x2*(y3-y1)+x3*(y1-y2)
        if abs(det)<100000:
            self.cal_points=[]; self.say('Targets too close. Try again.'); return
        def solve(z):
            z1,z2,z3=z
            return [(z1*(y2-y3)+z2*(y3-y1)+z3*(y1-y2))/det,
                    (x1*(z2-z3)+x2*(z3-z1)+x3*(z1-z2))/det,
                    (x1*(y3*z2-y2*z3)+x2*(y1*z3-y3*z1)+x3*(y2*z1-y1*z2))/-det]
        result=solve([p[0] for p in dst])+solve([p[1] for p in dst])
        for (x,y),(xx,yy) in zip(src,dst):
            if abs(result[0]*x+result[1]*y+result[2]-xx)>1 or abs(result[3]*x+result[4]*y+result[5]-yy)>1:
                self.cal_points=[]; self.say('Calibration failed. Retry.'); return
        self.cal_candidate=result
        self.say('Tap the final target to check accuracy.')

    def tap(self,start,end,rawx,rawy):
        x,y=self.position(rawx,rawy)
        if self.waking:
            self.waking=False; return
        if self.mode=='calibrate':
            self.calibration_tap(rawx,rawy); return
        if self.mode=='emergency':
            self.form_start('recover'); return
        for rect,label,action in self.buttons:
            left,top,right,bottom=rect
            if left<=x<=right and top<=y<=bottom:
                self.button(action); return
        if self.mode=='status':
            self.page=(self.page+1)%3; self.last_render=0

    def button(self,action):
        if action=='admin': self.form_start('login' if self.state['enrolled'] else 'enroll')
        elif action=='lockprompt':
            if not self.state['enrolled']:
                self.form_start('enroll'); self.say('Set both PINs before using Lock.')
            else:
                self.confirm_id='local-emergency'; self.mode='confirm'
                self.lines=['Activate security lock?', 'Mumble will keep running.', 'Your separate recovery PIN will be required to unlock.']
                self.confirm_until=time.monotonic()+30
        elif action=='cancel':
            if self.state.get('emergency'):
                self.clear_secrets(); self.mode='emergency'
            elif self.token:
                self.clear_secrets(); self.mode='admin'
            else: self.lock()
        elif action=='lock': self.lock()
        elif action=='enter':
            if self.mode=='form': self.form_submit()
            else: self.execute()
        elif action=='back': self.input=self.input[:-1]
        elif action=='shift': self.shift=not self.shift
        elif action=='symbols': self.symbols=not self.symbols
        elif action=='up': self.offset=max(0,self.offset-4)
        elif action=='down': self.offset+=4
        elif action=='help': self.input='help'; self.execute()
        elif action=='users': self.input='users'; self.execute()
        elif action=='confirm':
            identity=self.confirm_id; self.confirm_id=''
            if identity=='local-emergency':
                if time.monotonic()<=self.confirm_until: self.emergency()
                else: self.mode='status'; self.say('Confirmation expired. Tap Lock again.')
                return
            try: self.apply(self.call('confirm',id=identity))
            except Exception as exc: self.mode='admin'; self.lines=[str(exc)]
        elif action=='calibrate': self.cal_points=[]; self.cal_candidate=None; self.cal_last=0; self.mode='calibrate'
        elif action.startswith('key:'):
            key=action[4:]
            if self.shift: key=key.upper()
            if len(self.input)<128: self.input+=key

    def text(self,draw,x,y,value,size=22,color=FG):
        draw.text((x,y),str(value),font=self.fonts[size],fill=color)

    def btn(self,draw,rect,label,action,color=PANEL):
        draw.rounded_rectangle(rect,radius=5,fill=color,outline='#305363')
        font=self.fonts[22]; box=draw.textbbox((0,0),label,font=font)
        x=(rect[0]+rect[2]-box[2])/2; y=(rect[1]+rect[3]-(box[3]-box[1]))/2-box[1]
        draw.text((x,y),label,font=font,fill=FG); self.buttons.append((rect,label,action))

    def keyboard(self,draw,numeric=False):
        if numeric:
            keys=[['1','2','3'],['4','5','6'],['7','8','9'],['Back','0','Enter']]
            for row,values in enumerate(keys):
                for col,label in enumerate(values):
                    action={'Back':'back','Enter':'enter'}.get(label,'key:'+label)
                    self.btn(draw,(100+col*148,192+row*69,240+col*148,255+row*69),label,action)
            return
        rows=['1234567890','qwertyuiop','asdfghjkl','zxcvbnm']
        if self.symbols: rows=['!@#$%^&*()','-_=+[]{}<>','/\\:;\"\'?,.','`~|']
        for row,values in enumerate(rows):
            start=(640-len(values)*63)//2
            for col,key in enumerate(values):
                self.btn(draw,(start+col*63,288+row*37,start+col*63+59,321+row*37),key.upper() if self.shift else key,'key:'+key)
        for col,(label,action) in enumerate([('Shift','shift'),('Space','key: '),('ABC' if self.symbols else 'Sym','symbols'),('Back','back'),('Enter','enter')]):
            self.btn(draw,(2+col*128,438,125+col*128,477),label,action)

    def image(self):
        im=Image.new('RGB',(W,H),BG); draw=ImageDraw.Draw(im); self.buttons=[]
        draw.rectangle((0,0,W,43),fill=PANEL)
        draw.text((12,1),'TacComms',font=self.header_font,fill=CYAN)
        title={'status':'STATUS','admin':'ADMIN','form':'SECURE ENTRY','confirm':'CONFIRM','emergency':'LOCKED','calibrate':'TOUCH SETUP'}[self.mode]
        if self.mode=='status': title=('Status','Logs','Processes')[self.page]+' '+str(self.page+1)+'/3'
        self.text(draw,620-len(title)*13,10,title,20,RED if self.state.get('emergency') else MUTED)
        draw.line((12,46,627,46),fill=CYAN,width=2)
        if self.mode=='calibrate':
            i=min(len(self.cal_points),3); x,y=[(70,80),(570,80),(320,400),(510,355)][i]
            self.text(draw,75,190,'Tap the target with the stylus',24)
            self.text(draw,170,228,f'Target {i+1} of 4',24,CYAN)
            draw.ellipse((x-25,y-25,x+25,y+25),outline=CYAN,width=3)
            draw.line((x-35,y,x+35,y),fill=FG,width=2); draw.line((x,y-35,x,y+35),fill=FG,width=2)
        elif self.mode=='status':
            if self.page==0:
                lines=self.status
            elif self.page==1:
                logs=self.legacy.sample('menu-logs',5,lambda:command('journalctl','-b','-u','mumble-server.service','-n','8','--no-pager','--output=cat')[1])
                lines=[part for line in logs.splitlines() for part in (textwrap.wrap(line,42) or [''])][-10:] or ['No server messages yet.']
            else:
                lines=self.legacy.sample('menu-processes',5,self.legacy.process_lines)[:10]
            for i,line in enumerate(lines[:10]): self.text(draw,14,57+i*31,line,24,GREEN if self.page==0 and i==0 else FG)
            next_view=('Logs','Processes','Status')[self.page]
            self.text(draw,14,381,'Tap main area: '+next_view,20,CYAN)
            remain=max(0,60-int(time.monotonic()-self.last_touch))
            sleep=f'Sleep {remain}s' if self.legacy.bus and 'unavailable' not in self.legacy.power_mode else 'Sleep retrying'
            self.text(draw,620-len(sleep)*11,383,sleep,18,MUTED)
            self.btn(draw,(13,416,307,475),'Admin' if self.state.get('enrolled') else 'Set PINs','admin')
            self.btn(draw,(332,416,626,475),'Lock','lockprompt')
        elif self.mode=='emergency':
            self.text(draw,92,115,'EMERGENCY LOCK',32,RED)
            self.text(draw,48,190,'Mumble continues running.',28)
            self.text(draw,48,242,'Admin controls are locked.',24)
            self.text(draw,48,300,'Separate recovery PIN required.',22)
            self.btn(draw,(95,367,545,438),'Enter recovery PIN','recover')
        elif self.mode=='form':
            label=self.form[self.form_index][1]
            self.text(draw,20,62,label,28)
            self.btn(draw,(505,53,627,96),'Cancel','cancel')
            hint='Six digits; recovery must be different.' if self.form_kind=='enroll' else 'Input is hidden and is never logged.'
            self.text(draw,20,106,hint,20,MUTED)
            self.text(draw,20,141,'*'*min(len(self.input),35),32,CYAN)
            self.keyboard(draw,numeric=self.form_kind!='password')
        elif self.mode=='confirm':
            yy=85
            for line in self.lines:
                for wrapped in textwrap.wrap(line,38):
                    self.text(draw,24,yy,wrapped,24); yy+=34
            self.text(draw,24,270,'Confirmation expires after 30s.',20,MUTED)
            self.btn(draw,(25,346,303,413),'Cancel','cancel')
            self.btn(draw,(332,346,612,413),'Confirm','confirm',color='#63322b')
        else:
            for col,(label,action) in enumerate([('Help','help'),('Users','users'),('Up','up'),('Down','down'),('Exit','lock')]):
                self.btn(draw,(2+col*128,48,125+col*128,86),label,action)
            if self.user_view:
                limit=max(0,len(self.users)-4); self.offset=min(self.offset,limit)
                if not self.users: self.text(draw,15,110,'No clients connected.',24)
                for i,u in enumerate(self.users[self.offset:self.offset+4]):
                    y=95+i*37; color=GREEN if u['speaking'] else MUTED
                    draw.polygon([(15,y+10),(23,y+10),(34,y+1),(34,y+25),(23,y+17),(15,y+17)],fill=color)
                    if u['speaking']:
                        draw.arc((24,y-5,50,y+30),-70,70,fill=color,width=3)
                    label=f"{u['session']} {u['name']}"+(' [mute]' if u['muted'] else '')
                    self.text(draw,57,y,label[:40],22,color)
                    self.text(draw,300,y+21,u['ip']+(' TCP' if u['tcp_only'] else ' UDP'),18,MUTED)
            else:
                lines=[part for line in self.lines for part in (textwrap.wrap(line,46) or [''])]
                self.offset=min(self.offset,max(0,len(lines)-6))
                for i,line in enumerate(lines[self.offset:self.offset+6]): self.text(draw,12,94+i*25,line,22)
            draw.rectangle((6,248,633,281),fill=PANEL)
            self.text(draw,12,250,'> '+self.input[-43:]+'_',22,CYAN)
            self.keyboard(draw)
        if self.message and time.monotonic()<self.message_until:
            # PIN keys remain visible; short overlay above them for validation errors.
            y=164 if self.mode=='form' else 354 if self.mode=='status' else 444
            draw.rectangle((0,y,W,y+27),fill='#693727')
            self.text(draw,6,y+1,self.message[:56],18,FG)
        return im

    def loop(self):
        fd=os.open('/dev/fb0',os.O_RDWR)
        info=bytearray(160); fcntl.ioctl(fd,0x4600,info,True)
        values=struct.unpack_from('20I',info)
        if values[:2]!=(W,H) or values[6]!=16 or (values[8],values[11],values[14])!=(11,5,0):
            raise RuntimeError('Unsupported framebuffer; expected 640x480 RGB565.')
        stride=int(Path('/sys/class/graphics/fb0/stride').read_text())
        fb=mmap.mmap(fd,stride*H)
        # systemd opens the assigned TTY before dropping to the UI account.
        ttyfd=os.dup(sys.stdin.fileno())
        fcntl.ioctl(ttyfd,0x4b3a,1)  # KD_GRAPHICS: kernel text cannot overwrite the UI.
        touch=Touch(self.events); touch.start()
        try:
            for attempt in range(3):
                self.legacy.find_ddc()
                if self.legacy.bus: break
                time.sleep(0.4)
            self.legacy.set_blank(False)
            self.last_power_probe=time.monotonic()
            self.last_touch=time.monotonic()
            self.state=wait_ready()
            self.mode='emergency' if self.state['emergency'] else 'status' if self.calibration else 'calibrate'
            previous=None
            while self.running:
                now=time.monotonic()
                probing=self.power_probe is not None and self.power_probe.is_alive()
                if (not self.asleep and not probing and now-self.last_power_probe>=30
                        and (not self.legacy.bus or 'unavailable' in self.legacy.power_mode)):
                    self.last_power_probe=now
                    # DDC retries can be slow; keep input and PIN handling responsive.
                    self.power_probe=threading.Thread(target=self.legacy.find_ddc,daemon=True)
                    self.power_probe.start(); probing=True
                active=False; taps=[]
                while True:
                    try: ev=self.events.get_nowait()
                    except queue.Empty: break
                    if ev[0]=='down':
                        active=True; self.last_touch=now
                        if self.asleep:
                            self.legacy.set_blank(False); self.asleep=False; self.waking=True
                    elif ev[0]=='tap': taps.append(ev[1:])
                if active and self.token:
                    try: self.call('activity')
                    except Exception: self.lock()
                # Handle complete press/release taps in their original order.
                for tap in taps: self.tap(*tap)
                if taps or active: self.last_render=0
                if now-self.last_touch>=60:
                    if self.token or self.mode=='form':
                        self.lock(); self.mode='emergency' if self.state.get('emergency') else 'status'
                    if not self.asleep and not probing:
                        self.legacy.set_blank(True); self.asleep=self.legacy.asleep
                if now-self.last_state>=2:
                    try:
                        self.state=self.call('state')
                        if self.state['emergency'] and not (self.mode=='form' and self.form_kind=='recover'):
                            self.lock(); self.mode='emergency'
                    except Exception:
                        if self.token: self.lock()
                        self.say('Admin service unavailable. Controls locked.')
                    self.last_state=now
                if not self.asleep:
                    if now-self.last_status>=5:
                        self.status=self.legacy.status_lines(); self.last_status=now
                    if self.mode=='admin' and self.user_view and now-self.last_users>=0.4:
                        try: self.users=self.call('users')['users']
                        except Exception as exc: self.say(str(exc)); self.user_view=False
                        self.last_users=now
                    if now-self.last_render>=(0.4 if self.user_view else 1.0):
                        raw=rgb565(self.image())
                        if raw!=previous:
                            if stride==W*2: fb[:]=raw
                            else:
                                for y in range(H): fb[y*stride:y*stride+W*2]=raw[y*W*2:(y+1)*W*2]
                            previous=raw
                        self.last_render=now
                time.sleep(0.012 if not self.asleep else 0.15)
        finally:
            touch.running=False; touch.join(timeout=2)
            if self.power_probe: self.power_probe.join(timeout=13)
            self.lock(); self.legacy.set_blank(False)
            fcntl.ioctl(ttyfd,0x4b3a,0); os.close(ttyfd); fb.close(); os.close(fd)


if __name__=='__main__':
    screen=Screen()
    def stop(*args): screen.running=False
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    screen.loop()
