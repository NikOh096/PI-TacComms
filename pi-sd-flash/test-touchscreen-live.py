import json,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,'/opt/taccomms')
import screen
from PIL import Image
assert screen.rgb565(Image.new('RGB',(1,1),'red'))==b'\x00\xf8'
ui=screen.Screen(preview=True)
ui.state={'enrolled':True,'emergency':False}; ui.calibration=[1,0,0,0,1,0]
activated=[]; ui.emergency=lambda:activated.append(True)
ui.image(); ui.waking=True
ui.tap(0,.04,250,200); assert ui.page==0,'Wake tap changed the page'
for i in range(5):ui.tap(i*.1,i*.1+.04,250,200)
assert ui.page==2 and not activated,'Page taps unexpectedly locked the device'
ui.image(); ui.tap(1,1.05,450,440)
assert ui.mode=='confirm' and not activated,'Lock skipped confirmation'
ui.button('cancel'); assert ui.mode=='status' and not activated
ui.button('lockprompt'); ui.button('confirm'); assert activated==[True]
ui.mode='status'; ui.button('admin'); assert ui.mode=='form' and ui.form_kind=='login'
ui=screen.Screen(preview=True); ui.mode='admin'; ui.image()
activated=[]; ui.emergency=lambda:activated.append(True)
key=next(rect for rect,label,action in ui.buttons if action=='key:q')
x=(key[0]+key[2])/2; y=(key[1]+key[3])/2
ui.calibration=[1,0,0,0,1,0]
for i in range(5):ui.tap(i*.1,i*.1+.04,x,y)
assert ui.input=='qqqqq' and not activated, 'Keyboard taps accidentally locked the screen'
with tempfile.TemporaryDirectory(prefix='touch-calibration-test-') as folder:
    screen.CAL=Path(folder)/'touch.json'
    ui=screen.Screen(preview=True); ui.mode='calibrate'
    def raw(x,y):return (3900-y*7,240+x*5)
    for x,y in ((70,80),(570,80),(320,400)):
        ui.cal_last=0; ui.calibration_tap(*raw(x,y))
    assert ui.cal_candidate is not None and not screen.CAL.exists()
    ui.cal_last=0;ui.calibration_tap(*raw(70,80))
    assert ui.cal_candidate is None and not screen.CAL.exists(), 'Bad check target saved calibration'
    for x,y in ((70,80),(570,80),(320,400),(510,355)):
        ui.cal_last=0;ui.calibration_tap(*raw(x,y))
    assert screen.CAL.exists()
    x,y=ui.position(*raw(120,280))
    assert abs(x-120)<1 and abs(y-280)<1
print('PASS: RGB565 colors, wake tap, page cycling, Admin PIN prompt, Lock confirmation/cancel, keyboard input, swapped/inverted axes, calibration accuracy checks.')
