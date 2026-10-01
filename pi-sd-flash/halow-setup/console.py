#!/usr/bin/python3
"""TacComms status console with touch wake and HDMI backlight suspend."""
import os
from pathlib import Path
import re
import select
import shutil
import signal
import struct
import subprocess
import sys
import termios
import textwrap
import time
import tty

TIMEOUT = 60
EVENT = struct.Struct('qqHHi')  # Linux arm64 input_event


def command(*args, timeout=3):
    try:
        result = subprocess.run(args, text=True, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, timeout=timeout,
                                env=dict(os.environ, LC_ALL='C'))
        return result.returncode, result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ''


def plain(text):
    # Network-derived log messages must never be interpreted as terminal escapes.
    return ''.join(c if 32 <= ord(c) < 127 else ' ' for c in text)


def read_text(name, default=''):
    try:
        return Path(name).read_text().strip()
    except OSError:
        return default


def format_uptime(seconds):
    minutes = max(0, int(seconds)) // 60
    days, minutes = divmod(minutes, 1440)
    hours, minutes = divmod(minutes, 60)
    return (str(days) + 'd ' if days else '') + str(hours) + 'h ' + str(minutes) + 'm'


def display_command(bus, *args, timeout=12):
    # Match the command path verified on this OSOYOO HDMI35 at a 50 kHz DDC clock.
    # Access remains available in suspend; fixed delays avoid unreliable timing
    # learned from the previous failing clock setting.
    return command('ddcutil', '--bus', bus, '--skip-ddc-checks', '--mccs', '2.2',
                   '--disable-dynamic-sleep', '--sleep-multiplier', '2',
                   *args, timeout=timeout)


class Console:
    def __init__(self):
        self.last_touch = time.monotonic()
        self.last_frame = 0
        self.last_probe = -100
        self.page = 0
        self.asleep = False
        self.bus = None
        self.fds = {}
        self.power_mode = 'Backlight sleep: unavailable'
        self.running = True
        self.last_charger_low = None
        self.cache = {}
        self.last_lines = []
        self.frame_size = None

    def devices(self):
        for path in Path('/sys/class/input').glob('event*/device/name'):
            event = '/dev/input/' + path.parents[1].name
            if event in self.fds.values():
                continue
            try:
                fd = os.open(event, os.O_RDONLY | os.O_NONBLOCK)
                self.fds[fd] = event
            except OSError:
                pass

    def find_ddc(self):
        if not shutil.which('ddcutil'):
            return
        connected = []
        for path in Path('/sys/class/drm').glob('card*-HDMI-A-*'):
            try:
                if (path / 'status').read_text().strip() == 'connected' and (path / 'ddc').exists():
                    bus = (path / 'ddc').resolve().name
                    if re.fullmatch(r'i2c-\d+', bus):
                        connected.append(bus.split('-')[1])
            except OSError:
                pass
        if len(connected) == 1:
            code, reply = display_command(connected[0], 'getvcp', 'D6')
            if code == 0 and 'unsupported' not in reply.lower():
                self.bus = connected[0]
                self.power_mode = 'LCD suspend / tap to wake'
                print('DDC power control detected on bus ' + self.bus, file=sys.stderr, flush=True)

    def set_blank(self, asleep):
        if asleep and (not self.bus or 'unavailable' in self.power_mode):
            # Keeping useful status visible is preferable to an illuminated black
            # screen when this monitor cannot actually enter low-power mode.
            return
        if self.bus:
            # OSOYOO HDMI35 specifically defines D6=3 as suspend; D6=1 wakes it.
            # GPIO/SPI touch and the Pi remain powered. D6=4 is not supported by this model.
            code, reply = display_command(self.bus, 'setvcp', 'D6', '3' if asleep else '1')
            if code:
                self.power_mode = 'Backlight sleep: unavailable'
                print('DDC power command failed: ' + plain(reply), file=sys.stderr, flush=True)
                if asleep:
                    # A write may have succeeded even when verification failed.
                    # Attempt to restore power and keep the status view running.
                    display_command(self.bus, 'setvcp', 'D6', '1')
                    asleep = False
            else:
                self.power_mode = 'LCD suspend / tap to wake'
                print('Display suspended' if asleep else 'Display awake', file=sys.stderr, flush=True)
        # Always restore the video signal on wake, including when the previous console
        # version left the framebuffer blank. DDC handles the backlight independently.
        if not asleep:
            # This controls the local virtual console; no server process is suspended.
            subprocess.run(['setterm', '--blank', 'poke'],
                           stdin=sys.stdin, stdout=sys.stdout, stderr=subprocess.DEVNULL,
                           env=dict(os.environ, TERM='linux'), timeout=5)
        self.asleep = asleep
        if not asleep:
            self.last_frame = 0
            self.last_lines = []

    def activity(self, now):
        self.last_touch = now
        if self.asleep:
            self.set_blank(False)
        else:
            self.page = (self.page + 1) % 3
            self.last_frame = 0

    def sample(self, key, interval, reader):
        now = time.monotonic()
        stamp, value = self.cache.get(key, (float('-inf'), None))
        if now - stamp >= interval:
            value = reader()
            self.cache[key] = (time.monotonic(), value)
        return value

    def status_lines(self):
        _, details = command('systemctl', 'show', 'mumble-server.service',
                             '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID')
        service = dict(line.split('=', 1) for line in details.splitlines() if '=' in line)
        active = service.get('ActiveState', 'unknown')
        running = active == 'active' and service.get('SubState') == 'running'
        state = 'RUNNING' if running else active.upper()
        _, ethernet = command('ip', '-4', '-o', 'addr', 'show', 'dev', 'eth0', 'scope', 'global')
        ips = re.findall(r'inet ([\d.]+)/', ethernet)
        address = ips[0] if ips else ('waiting for IP' if read_text('/sys/class/net/eth0/carrier') == '1' else 'cable unplugged')
        phase = read_text('/boot/firmware/halow-setup/setup-state.txt')
        try:
            temp = str(round(int(read_text('/sys/class/thermal/thermal_zone0/temp')) / 1000)) + ' C'
        except ValueError:
            temp = '--'
        try:
            uptime = format_uptime(float(read_text('/proc/uptime').split()[0]))
        except (ValueError, IndexError):
            uptime = '--'
        load = (read_text('/proc/loadavg').split() or ['--'])[0]
        _, throttle = command('vcgencmd', 'get_throttled')
        match = re.search(r'0x([0-9a-fA-F]+)', throttle)
        flags = int(match.group(1), 16) if match else None
        supply = 'LOW VOLTAGE' if flags is not None and flags & 1 else 'OK' if flags is not None else 'unknown'
        _, pin = command('pinctrl', 'get', '3')
        level = re.search(r'\bip\b.*\|\s*(hi|lo)\b', pin)
        charger_low = level.group(1) == 'lo' if level else None
        # S Plus Auto=ON reports external input only, not battery charge current.
        charger = ('connected' if charger_low else 'disconnected') if charger_low is not None and charger_low == self.last_charger_low else 'unavailable' if charger_low is None else 'checking'
        self.last_charger_low = charger_low
        lines = ['Server    ' + state,
                 'Address   ' + address,
                 'Port      64738 TCP/UDP', '',
                 'Battery   -- (sensor needed)',
                 'Power in  ' + charger,
                 'Pi power  ' + supply,
                 'CPU       ' + temp + '   Load ' + load,
                 'Uptime    ' + uptime]
        if 'FAILED' in phase:
            lines.append('SETUP ERROR: inspect provision.log')
        elif phase and phase != 'PROVISION COMPLETE':
            lines.append(phase)
        elif not running:
            lines.append('Server stopped - check Logs')
        elif not self.bus or 'unavailable' in self.power_mode:
            lines.append('Display sleep unavailable')
        return lines

    def process_lines(self):
        _, output = command('ps', '-eo', 'pid=,pcpu=,comm=', '--sort=-pcpu')
        processes = []
        for line in output.splitlines():
            fields = line.split(None, 2)
            if len(fields) == 3 and fields[0].isdigit() and fields[2] != 'ps':
                processes.append(fields)
        # Keep the appliance's main service visible even when its CPU use is low.
        processes.sort(key=lambda item: item[2] not in ('mumble-server', 'murmurd'))
        return ['  PID  CPU% PROCESS'] + [
            pid.rjust(5) + ' ' + cpu.rjust(5) + ' ' + name
            for pid, cpu, name in processes] if processes else ['Process status unavailable.']

    def frame(self, columns, rows):
        width = max(1, columns - 1)
        title = ('Status', 'Logs', 'Processes')[self.page] + ' ' + str(self.page + 1) + '/3'
        header = 'TacComms' + ' ' * max(1, width - 8 - len(title)) + title
        lines = [header, '-' * width]
        available = max(0, rows - 4)
        if self.page == 0:
            lines += self.sample('status', 5, self.status_lines)
        elif self.page == 1:
            logs = self.sample('logs', 5, lambda: command(
                'journalctl', '-b', '-u', 'mumble-server.service', '-n', '8',
                '--no-pager', '--output=cat')[1])
            wrapped = []
            for line in logs.splitlines():
                wrapped += textwrap.wrap(plain(line), width=width) or ['']
            lines += (wrapped[-available:] if available else []) or ['No server messages yet.']
        else:
            lines += self.sample('processes', 5, self.process_lines)[:available]
        lines = [plain(line)[:width] for line in lines[:max(0, rows - 2)]]
        lines += [''] * max(0, rows - 2 - len(lines))
        next_view = ('logs', 'processes', 'status')[self.page]
        if self.bus and 'unavailable' not in self.power_mode:
            remaining = max(0, TIMEOUT - int(time.monotonic() - self.last_touch))
            footer = 'Tap: ' + next_view + ' | sleep ' + str(remaining) + 's'
        else:
            footer = 'Tap: ' + next_view + ' | sleep unavailable'
        return lines + [footer[:width]]

    def render(self):
        try:
            columns, rows = os.get_terminal_size(sys.stdout.fileno())
        except OSError:
            columns, rows = (40, 15)
        lines = self.frame(columns, rows)
        output = []
        if self.frame_size != (columns, rows):
            self.frame_size = (columns, rows)
            self.last_lines = []
            output.append('\x1b[0;37;40m\x1b[2J\x1b[?25l')
        for index, line in enumerate(lines):
            if index >= len(self.last_lines) or self.last_lines[index] != line:
                color = '\x1b[1;36;40m' if index == 0 else '\x1b[0;37;40m'
                output.append('\x1b[' + str(index + 1) + ';1H' + color + '\x1b[2K' + line)
        if output:
            sys.stdout.write(''.join(output) + '\x1b[0;37;40m')
            sys.stdout.flush()
        self.last_lines = lines

    def loop(self):
        saved = termios.tcgetattr(sys.stdin.fileno())
        tty.setraw(sys.stdin.fileno())
        sys.stdout.write('\x1b[0m\x1b[2J\x1b[H')
        sys.stdout.flush()
        # The app owns the one-minute timer so SPI touch can wake the display.
        subprocess.run(['setterm', '--blank', '0'], stdin=sys.stdin, stdout=sys.stdout,
                       stderr=subprocess.DEVNULL, timeout=5)
        try:
            self.find_ddc()
            self.set_blank(False)
            self.last_touch = time.monotonic()
            while self.running:
                now = time.monotonic()
                if now - self.last_probe >= 30:
                    self.devices()
                    # Probe display power control once at startup. A failed DDC
                    # transaction can block for seconds and delay touch handling.
                    self.last_probe = now
                if (self.bus and 'unavailable' not in self.power_mode
                        and not self.asleep and now - self.last_touch >= TIMEOUT):
                    self.set_blank(True)
                if not self.asleep and now - self.last_frame >= 1:
                    self.render()
                    self.last_frame = now
                # Input wakes select immediately; suspended screens need no rapid polling.
                ready, _, _ = select.select([sys.stdin.fileno(), *self.fds], [], [], 5 if self.asleep else 0.5)
                touched = False
                for fd in ready:
                    if fd == sys.stdin.fileno():
                        os.read(fd, 128)
                        touched = True
                        continue
                    try:
                        payload = os.read(fd, EVENT.size * 64)
                        if not payload:
                            raise OSError('Device disconnected')
                        for offset in range(0, len(payload) - EVENT.size + 1, EVENT.size):
                            _, _, kind, code, value = EVENT.unpack_from(payload, offset)
                            if kind == 1 and value == 1 and (code == 330 or code >= 256):
                                touched = True
                    except OSError:
                        os.close(fd)
                        self.fds.pop(fd, None)
                if touched:
                    self.activity(time.monotonic())
        finally:
            self.set_blank(False)
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, saved)
            sys.stdout.write('\x1b[?25h')
            sys.stdout.flush()
            for fd in self.fds:
                os.close(fd)


if __name__ == '__main__':
    console = Console()
    def stop(signum, frame):
        console.running = False
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    console.loop()
