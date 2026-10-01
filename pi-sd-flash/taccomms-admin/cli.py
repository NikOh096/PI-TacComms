#!/usr/bin/python3
"""Local admin CLI; commands are the same allowlist as on the touchscreen."""
import getpass
import json
from client import request

def main():
    state=request('state')
    if not state['enrolled']:
        print('Set up your two six-digit PINs on the Pi screen first.'); return
    if state['emergency']:
        request('recover',pin=getpass.getpass('Emergency recovery PIN: '))
    token=request('login',pin=getpass.getpass('Admin PIN: '))['token']
    try:
        while True:
            line=input('TacComms> ')
            try:
                answer=request('command',token=token,line=line)
                if answer.get('prompt'):
                    kind=answer['prompt']; fields={}
                    if kind=='recovery': fields['old']=getpass.getpass('Current recovery PIN: ')
                    fields['new']=getpass.getpass('New value: ')
                    fields['confirm']=getpass.getpass('Confirm: ')
                    answer=request('secret',token=token,kind=kind,**fields)
                for text in answer.get('lines',[]): print(text)
                if answer.get('confirm') and input('Type YES to confirm: ')=='YES':
                    answer=request('confirm',token=token,id=answer['confirm'])
                    for text in answer.get('lines',[]): print(text)
                for user in answer.get('users',[]): print(json.dumps(user,ensure_ascii=False))
                if answer.get('logout') or answer.get('emergency'): break
            except RuntimeError as exc: print(str(exc))
    finally:
        request('logout',token=token)

if __name__=='__main__':
    try: main()
    except (KeyboardInterrupt,EOFError): print()
    except RuntimeError as exc: print(str(exc))
