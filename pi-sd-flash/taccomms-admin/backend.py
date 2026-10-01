#!/usr/bin/python3
"""Local authenticated control service. No shell commands or network listener."""
import datetime
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import shlex
import shutil
import socket
import socketserver
import sqlite3
import struct
import subprocess
import time
import noise_control

from security import SecurityStore, SecurityError

DATA = Path('/var/lib/taccomms')
SOCKET = '/run/taccomms/admin.sock'

HELP = {
    'help': ['help [users|access|channels|system|audio]', 'IDs below come from users/channels/bans.'],
    'audio': ['noise status', 'noise on  (noise suppression + peak limiter)',
              'noise off  (original audio)', 'Changes apply without disconnecting calls.'],
    'users': ['users  (live names + speaker activity)', 'devices  (client IP, ID, transport)',
              'kick SESSION [reason]', 'mute SESSION on|off', 'deafen SESSION on|off',
              'move SESSION CHANNEL', 'priority SESSION on|off'],
    'access': ['password set  (masked prompt)', 'password clear  (confirmation)',
               'register SESSION  (certificate identity)', 'registrations',
               'revoke USERID  (ban cert + unregister)', 'ban SESSION [reason]  (certificate ban)',
               'bans', 'unban HASH  (from bans)', 'pin admin', 'pin recovery',
               'lock  (leave admin)', 'emergency  (separate recovery PIN)'],
    'channels': ['channels', 'channel add PARENT "Name"', 'channel rename ID "Name"',
                 'channel delete ID  (includes children)'],
    'system': ['status', 'health', 'crashlog  (save diagnostic report)', 'network', 'processes', 'logs [1..100]', 'audit [1..100]',
               'backup  (protected local snapshot)', 'server start|stop|restart',
               'reboot', 'shutdown', 'calibrate  (touchscreen)',
               'Ctrl commands are not a Linux shell.'],
}


def clean(value, limit=180):
    return ''.join(c if c.isprintable() else ' ' for c in str(value))[:limit]


def run(*args, timeout=10):
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                       env=dict(os.environ, LC_ALL='C'))
    if r.returncode:
        raise SecurityError('System command failed: ' + clean(args[0]))
    return r.stdout.strip()


def audit(event, **details):
    DATA.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = DATA/'audit.jsonl'
    if path.exists() and path.stat().st_size > 4_000_000:
        os.replace(path, DATA/'audit.previous.jsonl')
    record = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'event': event, **details}
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, 'a') as stream:
        stream.write(json.dumps(record, ensure_ascii=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


class Mumble:
    def __init__(self):
        import Ice
        Ice.loadSlice('-I/usr/share/ice/slice /usr/share/mumble-server/MumbleServer.ice')
        import MumbleServer
        self.api = MumbleServer
        self.ice = Ice.initialize(['taccomms', '--Ice.Warn.Connections=0'])
        self.secret = json.loads(Path('/etc/taccomms/ice.json').read_text())['secret']

    def server(self):
        proxy = self.ice.stringToProxy('s/1:tcp -h 127.0.0.1 -p 6502')
        return self.api.ServerPrx.uncheckedCast(proxy).ice_context({'secret': self.secret}).ice_invocationTimeout(2000)

    def users(self):
        result = []
        for sid, u in self.server().getUsers().items():
            address = ipaddress.ip_address(bytes(u.address))
            address = getattr(address, 'ipv4_mapped', None) or address
            result.append({'session': sid, 'userid': u.userid, 'name': clean(u.name, 60),
                           'channel': u.channel, 'ip': str(address), 'muted': bool(u.mute or u.selfMute or u.suppress),
                           'deaf': bool(u.deaf or u.selfDeaf), 'tcp_only': bool(u.tcponly),
                           'speaking': u.onlinesecs > 1 and u.idlesecs == 0 and not (u.mute or u.selfMute or u.suppress)})
        return sorted(result, key=lambda u: u['session'])

    def cert(self, sid):
        chain = self.server().getCertificateList(sid)
        if not chain:
            raise SecurityError('Client has no certificate. Set one in the client first.')
        return hashlib.sha1(bytes(chain[0])).hexdigest()

    def ban_cert(self, fingerprint, name, reason):
        s = self.server()
        bans = s.getBans()
        if not any(b.hash == fingerprint for b in bans):
            # All-zero /128 is an unspecified address, not a subnet ban. Identity
            # bans must not accidentally disconnect everyone behind the same router.
            bans.append(self.api.Ban(tuple([0]*16), 128, name, fingerprint, reason, int(time.time()), 0))
            s.setBans(bans)


class Admin:
    def __init__(self, mumble=None, security=None):
        self.security = security or SecurityStore(audit=audit)
        self.mumble = mumble or Mumble()
        self.pending = {}

    def response(self, lines=None, **extra):
        return {'lines': [clean(x, 300) for x in (lines or [])], **extra}

    def dispatch(self, request, uid, ui_uid):
        op = request.get('op')
        token = request.get('token', '')
        if op == 'state':
            return self.security.public_state()
        if op == 'enroll':
            if uid not in (0, ui_uid):
                raise SecurityError('Enroll PINs on the touchscreen.')
            self.security.enroll(*(request.get(k, '') for k in ('admin','admin_confirm','recovery','recovery_confirm')))
            return self.response(['PINs saved. Double tap to sign in.'])
        if op == 'login':
            return {'token': self.security.login(request.get('pin', ''), uid)}
        if op == 'recover':
            self.security.recover(request.get('pin', ''))
            self.pending.clear()
            return self.response(['Emergency lock cleared.'])
        if op == 'emergency':
            self.security.emergency()
            self.pending.clear()
            return self.response(['Emergency locked. Mumble keeps running.'])
        if op == 'logout':
            self.security.logout(token)
            self.pending.pop(token, None)
            return self.response()
        self.security.authorize(token, uid, touch=op in ('activity', 'command', 'confirm', 'secret'))
        if op == 'activity':
            return self.response()
        if op == 'users':
            return {'users': self.mumble.users()}
        if op == 'secret':
            kind = request.get('kind')
            new, confirm = request.get('new', ''), request.get('confirm', '')
            if kind == 'password':
                if not isinstance(new, str) or not 1 <= len(new) <= 128 or any(ord(c)<32 for c in new):
                    raise SecurityError('Use a password of 1 to 128 printable characters.')
                if new != confirm:
                    raise SecurityError('Password confirmation did not match.')
                audit('server_password_changed', uid=uid)
                self.mumble.server().setConf('password', new)
                return self.response(['Server password saved.', 'Existing calls remain connected.', 'New connections need the new password.'])
            if kind in ('admin', 'recovery'):
                self.security.change_pin(kind, new, confirm, request.get('old'))
                return self.response(['PIN saved. Sign in again.'], logout=True)
            raise SecurityError('Unknown secure prompt.')
        if op == 'confirm':
            item = self.pending.pop(token, None)
            if not item or item['until'] < time.monotonic() or not secrets.compare_digest(str(request.get('id', '')), item['id']):
                raise SecurityError('Confirmation expired. Run the command again.')
            # Re-enter parser after authentication; callbacks do not survive restarts.
            return self.command(item['line'], token, uid, confirmed=True, expected=item.get('expected'))
        if op == 'command':
            self.pending.pop(token, None)
            return self.command(request.get('line', ''), token, uid)
        raise SecurityError('Unknown operation.')

    def confirm(self, line, token, description, expected=None):
        identity = secrets.token_hex(16)
        self.pending = {t: v for t, v in self.pending.items() if v['until'] > time.monotonic()}
        self.pending[token] = {'line': line, 'until': time.monotonic()+30, 'id': identity, 'expected': expected}
        return self.response([description], confirm=identity)

    def command(self, line, token, uid, confirmed=False, expected=None):
        if not isinstance(line, str) or len(line)>512:
            raise SecurityError('Command too long.')
        try:
            args = shlex.split(line)
        except ValueError:
            raise SecurityError('Close the quotation marks.')
        if not args:
            return self.response()
        verb = args[0].lower()
        # Log only command names, never raw command text, PINs, or passwords.
        audit('admin_command', uid=uid, command=clean(verb, 24))
        if verb == 'help':
            if len(args)==1:
                return self.response([line for topic in HELP.values() for line in topic])
            if len(args)==2 and args[1] in HELP:
                return self.response(HELP[args[1]])
        if args == ['lock']:
            self.security.logout(token)
            return self.response(['Admin locked.'], logout=True)
        if args == ['emergency']:
            if not confirmed:
                return self.confirm(line,token,'Activate security lock? Recovery PIN will be required. Mumble keeps running.')
            self.security.emergency()
            self.pending.clear()
            return self.response(['Emergency locked.'], emergency=True)
        if args == ['calibrate']:
            return self.response(['Touch the calibration targets.'], calibrate=True)
        if args in (['health'], ['crashlog']):
            command=['/usr/bin/python3','/usr/local/lib/taccomms-diagnostics/monitor.py']
            if args==['health']:command.append('--brief')
            return self.response(run(*command,timeout=30).splitlines())
        if args in (['noise'], ['noise','status']):
            return self.response(noise_control.status())
        if args in (['noise','on'], ['noise','off']):
            try:
                lines=noise_control.set_mode(args[1])
            except ValueError as exc:
                raise SecurityError(str(exc))
            audit('noise_mode_changed', uid=uid, mode=args[1])
            return self.response(lines)
        if args in (['password','set'], ['pin','admin'], ['pin','recovery']):
            return self.response(prompt='password' if verb=='password' else args[1])
        if args == ['password','clear']:
            if not confirmed:
                return self.confirm(line, token, 'Remove the shared server password?')
            self.mumble.server().setConf('password', '')
            audit('server_password_removed', uid=uid)
            return self.response(['Shared password removed. Guests can join.'])
        if args == ['users'] or args == ['devices']:
            return self.response(users=self.mumble.users(), view=verb)
        if args == ['channels']:
            return self.response([f'{i}: {clean(c.name)} (parent {c.parent})' for i,c in sorted(self.mumble.server().getChannels().items())])
        if args == ['registrations']:
            return self.response([f'{i}: {clean(n)}' for i,n in sorted(self.mumble.server().getRegisteredUsers('').items())] or ['No registered users.'])
        if args == ['bans']:
            return self.response([f'{clean(b.name)} {b.hash or "IP ban"} {clean(b.reason)}' for b in self.mumble.server().getBans()] or ['No bans.'])
        if verb in ('kick','ban','register','mute','deafen','priority','move') and len(args)>=2 and args[1].isdigit():
            sid = int(args[1])
            s = self.mumble.server()
            user = s.getState(sid)
            if user.userid == 0:
                raise SecurityError('SuperUser cannot be changed here.')
            if verb in ('ban','kick'):
                try:
                    fingerprint = self.mumble.cert(sid)
                except SecurityError:
                    if verb=='ban': raise
                    fingerprint = ''
                target = {'sid': sid, 'cert': fingerprint, 'name': user.name, 'online_start': int(time.time())-user.onlinesecs}
                if not confirmed:
                    return self.confirm(line, token, verb.title() + ' ' + clean(user.name) + '?', target)
                if not expected or fingerprint!=expected['cert'] or user.name!=expected['name'] or abs(target['online_start']-expected['online_start'])>2:
                    raise SecurityError('Connection changed. Select the user again.')
                reason = ' '.join(args[2:])[:120] or 'Removed by TacComms admin'
                if verb=='ban':
                    self.mumble.ban_cert(fingerprint, user.name, reason)
                s.kickUser(sid, reason)
                return self.response([verb.title() + ' completed for ' + clean(user.name)])
            if verb=='register' and len(args)==2:
                if user.userid>=0:
                    raise SecurityError('Already registered as ID ' + str(user.userid))
                api=self.mumble.api
                identity=s.registerUser({api.UserInfo.UserName:user.name, api.UserInfo.UserHash:self.mumble.cert(sid)})
                return self.response([f'Registered ID {identity}. Reconnect the client.'])
            if verb in ('mute','deafen','priority') and len(args)==3 and args[2] in ('on','off'):
                setattr(user, {'mute':'mute','deafen':'deaf','priority':'prioritySpeaker'}[verb], args[2]=='on')
                if verb=='mute' and args[2]=='off':
                    user.deaf=False
                if verb=='deafen' and args[2]=='on':
                    user.mute=True
                s.setState(user)
                return self.response([verb.title() + ' ' + args[2] + ': ' + clean(user.name)])
            if verb=='move' and len(args)==3 and args[2].isdigit():
                user.channel=int(args[2]); s.setState(user)
                return self.response(['User moved.'])
        if verb=='revoke' and len(args)==2 and args[1].isdigit():
            identity=int(args[1])
            if identity==0:
                raise SecurityError('Cannot revoke SuperUser.')
            s=self.mumble.server(); api=self.mumble.api
            record=s.getRegistration(identity)
            fingerprint=record.get(api.UserInfo.UserHash, '')
            name=record.get(api.UserInfo.UserName, '')
            if not re.fullmatch('[a-fA-F0-9]{40}',fingerprint):
                raise SecurityError('No certificate on this registration. A certificate is required for safe revocation.')
            if not confirmed:
                return self.confirm(line, token, 'Ban certificate and revoke ' + clean(name) + '?', {'hash':fingerprint})
            if expected!={'hash':fingerprint}:
                raise SecurityError('Registration changed. Try again.')
            self.mumble.ban_cert(fingerprint, name, 'Access revoked')
            for sid,u in s.getUsers().items():
                if u.userid==identity:
                    s.kickUser(sid, 'Access revoked')
            s.unregisterUser(identity)
            return self.response(['Certificate banned; registration removed.', 'A new certificate is a new identity.', 'Rotate shared password if compromised.'])
        if verb=='unban' and len(args)==2 and re.fullmatch('[a-fA-F0-9]{40}',args[1]):
            if not confirmed:
                return self.confirm(line,token,'Remove this certificate ban?')
            s=self.mumble.server(); bans=s.getBans()
            kept=[b for b in bans if b.hash.lower()!=args[1].lower()]
            if len(kept)==len(bans):
                raise SecurityError('Ban not found. Copy the full hash from bans.')
            s.setBans(kept)
            return self.response(['Certificate ban removed.'])
        if verb=='channel' and len(args)>=3:
            action=args[1]
            if not args[2].isdigit():
                raise SecurityError('Channel ID must be a number.')
            cid=int(args[2]); s=self.mumble.server()
            if action=='add' and len(args)==4 and 1<=len(args[3])<=60:
                return self.response(['Channel created: '+str(s.addChannel(args[3],cid))])
            if action=='rename' and len(args)==4 and 1<=len(args[3])<=60:
                channel=s.getChannelState(cid); channel.name=args[3]; s.setChannelState(channel)
                return self.response(['Channel renamed.'])
            if action=='delete' and len(args)==3 and cid!=0:
                channel=s.getChannelState(cid)
                if not confirmed:
                    return self.confirm(line,token,'Delete '+clean(channel.name)+' and all children?', {'name':channel.name})
                if expected!={'name':channel.name}:
                    raise SecurityError('Channel changed. Try again.')
                s.removeChannel(cid)
                return self.response(['Channel removed.'])
        if verb in ('logs','audit') and (len(args)==1 or len(args)==2 and args[1].isdigit() and 1<=int(args[1])<=100):
            count=int(args[1]) if len(args)>1 else 30
            if verb=='logs':
                lines=run('journalctl','-u','mumble-server.service','-n',str(count),'--no-pager','-o','cat').splitlines()
            else:
                lines=(DATA/'audit.jsonl').read_text().splitlines()[-count:]
            return self.response(lines or ['No entries.'])
        if args==['status']:
            state=run('systemctl','show','mumble-server.service','-p','ActiveState','-p','MainPID')
            return self.response(state.splitlines()+['PINs configured; security lock ready.', 'Menu: Admin / Lock. Admin idle limit: 60s.'])
        if args==['network']:
            return self.response(run('ip','-brief','address').splitlines())
        if args==['processes']:
            return self.response(run('ps','-eo','pid,pcpu,comm','--sort=-pcpu').splitlines()[:25])
        if args==['backup']:
            dest=DATA/'backups'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            dest.mkdir(parents=True,mode=0o700)
            config=Path('/etc/mumble/mumble-server.ini')
            db='/var/lib/mumble-server/mumble-server.sqlite'
            for entry in config.read_text().splitlines():
                if entry.strip().startswith('database='):
                    db=entry.split('=',1)[1].strip()
            with sqlite3.connect('file:'+db+'?mode=ro',uri=True) as src, sqlite3.connect(dest/'mumble.sqlite') as dst:
                src.backup(dst)
            shutil.copy2(config,dest/config.name)
            for f in ('pins.json','security-state.json'):
                if (DATA/f).exists():
                    shutil.copy2(DATA/f,dest/f)
            for p in dest.iterdir(): p.chmod(0o600)
            return self.response(['Backup saved:', str(dest)])
        if verb=='server' and len(args)==2 and args[1] in ('start','stop','restart'):
            action=args[1]
            if action!='start' and not confirmed:
                return self.confirm(line,token,action.title()+' Mumble? Calls will disconnect.')
            # Keep unit enabled, and boot=true, so power-on startup is preserved.
            run('systemctl',action,'mumble-server.service',timeout=25)
            return self.response(['Mumble '+action+' completed. Automatic startup remains enabled.'])
        if args in (['reboot'],['shutdown']):
            if not confirmed:
                return self.confirm(line,token,verb.title()+' the Pi? Calls will disconnect.')
            audit('power_action', action=verb, uid=uid)
            run('systemctl','--no-block','reboot' if verb=='reboot' else 'poweroff')
            return self.response([verb.title()+' requested.'])
        raise SecurityError('Unknown command or arguments. Type help.')


def main():
    os.umask(0o077)
    app=Admin()
    ui_uid=pwd.getpwnam('taccomms').pw_uid
    allowed={0,ui_uid,pwd.getpwnam('niko').pw_uid}
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            self.connection.settimeout(3)
            try:
                _,uid,_=struct.unpack('3i',self.connection.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
                if uid not in allowed:
                    raise SecurityError('Local access denied.')
                raw=self.rfile.readline(8193)
                if len(raw)>8192 or not raw.endswith(b'\n'):
                    raise SecurityError('Invalid request.')
                request=json.loads(raw)
                if not isinstance(request,dict):
                    raise SecurityError('Invalid request.')
                answer={'ok':True,**app.dispatch(request,uid,ui_uid)}
            except SecurityError as exc:
                answer={'ok':False,'error':str(exc)}
            except Exception as exc:
                # Exception text may contain user input or configuration secrets.
                audit('operation_failed', type=type(exc).__name__)
                answer={'ok':False,'error':'Operation failed ('+type(exc).__name__+'). Check server status.'}
            try:
                self.wfile.write(json.dumps(answer).encode()+b'\n')
            except (OSError,BrokenPipeError):
                pass
    Path(SOCKET).unlink(missing_ok=True)
    with socketserver.UnixStreamServer(SOCKET,Handler) as server:
        os.chown(SOCKET,0,pwd.getpwnam('taccomms').pw_gid)
        os.chmod(SOCKET,0o660)
        audit('admin_backend_started')
        server.serve_forever(poll_interval=0.5)


if __name__=='__main__':
    main()
