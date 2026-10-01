"""Persistent PIN security for local TacComms controls (not disk encryption)."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import threading
import time


class SecurityError(Exception):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + '.new-' + secrets.token_hex(4))
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, separators=(',', ':'))
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != 'nt':
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def valid_pin(value):
    return isinstance(value, str) and re.fullmatch(r'[0-9]{6}', value) is not None


def pin_hash(pin, salt=None):
    if not valid_pin(pin):
        raise SecurityError('Use exactly six digits.')
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(pin.encode('ascii'), salt=salt, n=16384, r=8, p=1, dklen=32)
    return {'salt': salt.hex(), 'digest': digest.hex()}


def pin_matches(pin, record):
    if not valid_pin(pin):
        return False
    actual = pin_hash(pin, bytes.fromhex(record['salt']))['digest']
    return hmac.compare_digest(actual, record['digest'])


class SecurityStore:
    def __init__(self, directory='/var/lib/taccomms', clock=time.time, audit=None):
        self.directory = Path(directory)
        self.clock = clock
        self.audit = audit or (lambda event, **details: None)
        self.mutex = threading.RLock()
        self.sessions = {}
        self.pins_path = self.directory/'pins.json'
        self.state_path = self.directory/'security-state.json'
        self.pins = json.loads(self.pins_path.read_text()) if self.pins_path.exists() else None
        self.state = json.loads(self.state_path.read_text()) if self.state_path.exists() else {'emergency': False, 'failures': {}}

    def public_state(self):
        with self.mutex:
            return {'enrolled': self.pins is not None, 'emergency': bool(self.state['emergency']),
                    'retry_after': {role: max(0, int(self.state['failures'].get(role, {}).get('until', 0) - self.clock()) + 1)
                                    if self.state['failures'].get(role, {}).get('until', 0) > self.clock() else 0
                                    for role in ('admin', 'recovery')}}

    def enroll(self, admin, admin_confirm, recovery, recovery_confirm):
        with self.mutex:
            if self.pins is not None:
                raise SecurityError('PINs have already been configured.')
            if not valid_pin(admin) or not valid_pin(recovery):
                raise SecurityError('Both PINs must contain exactly six digits.')
            if admin != admin_confirm or recovery != recovery_confirm:
                raise SecurityError('PIN confirmation did not match.')
            if hmac.compare_digest(admin, recovery):
                raise SecurityError('Choose different admin and recovery PINs.')
            pins = {'version': 1, 'admin': pin_hash(admin), 'recovery': pin_hash(recovery)}
            self.audit('pins_enrolled')
            atomic_json(self.pins_path, pins)
            self.pins = pins
            atomic_json(self.state_path, self.state)

    def _check(self, role, pin):
        if self.pins is None:
            raise SecurityError('Set up both PINs on the screen first.')
        failure = self.state['failures'].get(role, {'count': 0, 'until': 0})
        remaining = failure['until'] - self.clock()
        if remaining > 0:
            raise SecurityError('Too many attempts. Retry in ' + str(int(remaining) + 1) + 's.')
        if not pin_matches(pin, self.pins[role]):
            count = failure['count'] + 1
            delay = min(900, 30 * (2 ** min(5, count - 5))) if count >= 5 else 0
            self.state['failures'][role] = {'count': count, 'until': self.clock() + delay}
            atomic_json(self.state_path, self.state)
            self.audit('pin_rejected', role=role, lockout_seconds=delay)
            raise SecurityError('Incorrect PIN.' + (' Retry in ' + str(delay) + 's.' if delay else ''))
        self.state['failures'][role] = {'count': 0, 'until': 0}
        atomic_json(self.state_path, self.state)

    def login(self, pin, uid):
        with self.mutex:
            if self.state['emergency']:
                raise SecurityError('Emergency lock requires the separate recovery PIN.')
            self._check('admin', pin)
            token = secrets.token_urlsafe(32)
            self.sessions[token] = {'uid': uid, 'until': self.clock() + 60}
            self.audit('admin_unlocked', uid=uid)
            return token

    def authorize(self, token, uid, touch=False):
        with self.mutex:
            session = self.sessions.get(token)
            if self.state['emergency'] or not session or session['uid'] != uid or session['until'] <= self.clock():
                self.sessions.pop(token, None)
                raise SecurityError('Admin session locked. Enter the admin PIN.')
            if touch:
                session['until'] = self.clock() + 60

    def logout(self, token):
        with self.mutex:
            self.sessions.pop(token, None)

    def emergency(self):
        with self.mutex:
            if self.pins is None:
                raise SecurityError('Set both PINs before enabling emergency lock.')
            self.audit('emergency_locked')
            self.state['emergency'] = True
            atomic_json(self.state_path, self.state)
            self.sessions.clear()

    def recover(self, pin):
        with self.mutex:
            self._check('recovery', pin)
            self.audit('emergency_recovered')
            self.state['emergency'] = False
            atomic_json(self.state_path, self.state)
            self.sessions.clear()

    def change_pin(self, role, new_pin, confirm, recovery_pin=None):
        with self.mutex:
            if role not in ('admin', 'recovery') or not valid_pin(new_pin):
                raise SecurityError('Use exactly six digits.')
            if new_pin != confirm:
                raise SecurityError('PIN confirmation did not match.')
            if role == 'recovery':
                self._check('recovery', recovery_pin)
            if pin_matches(new_pin, self.pins['recovery' if role == 'admin' else 'admin']):
                raise SecurityError('The admin and recovery PINs must be different.')
            updated = dict(self.pins)
            updated[role] = pin_hash(new_pin)
            self.audit('pin_changed', role=role)
            atomic_json(self.pins_path, updated)
            self.pins = updated
            self.sessions.clear()
