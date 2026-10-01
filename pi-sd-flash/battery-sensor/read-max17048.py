#!/usr/bin/env python3
"""Read an Adafruit MAX17048 on the dedicated battery I2C bus. No configuration writes."""
import argparse
import ctypes
import json
import os
import sys


def decode(voltage_raw, percent_raw, rate_raw):
    volts = voltage_raw * 0.000078125
    percent = percent_raw / 256.0
    signed_rate = rate_raw - 65536 if rate_raw & 0x8000 else rate_raw
    return volts, percent, signed_rate * 0.208


def read_battery(bus):
    if not sys.platform.startswith('linux'):
        raise RuntimeError('Run this reader on the Raspberry Pi, not on Windows.')

    class Message(ctypes.Structure):
        _fields_ = [('addr', ctypes.c_uint16), ('flags', ctypes.c_uint16),
                    ('length', ctypes.c_uint16), ('buffer', ctypes.POINTER(ctypes.c_uint8))]

    class Transfer(ctypes.Structure):
        _fields_ = [('messages', ctypes.POINTER(Message)), ('count', ctypes.c_uint32)]

    libc = ctypes.CDLL(None, use_errno=True)
    libc.ioctl.argtypes = [ctypes.c_int, ctypes.c_ulong, ctypes.c_void_p]
    libc.ioctl.restype = ctypes.c_int
    fd = os.open('/dev/i2c-' + str(bus), os.O_RDWR)
    try:
        def register(number):
            pointer = (ctypes.c_uint8 * 1)(number)
            reply = (ctypes.c_uint8 * 2)()
            messages = (Message * 2)(Message(0x36, 0, 1, pointer), Message(0x36, 1, 2, reply))
            transfer = Transfer(messages, 2)
            if libc.ioctl(fd, 0x0707, ctypes.byref(transfer)) < 0:
                code = ctypes.get_errno()
                raise OSError(code, os.strerror(code))
            return int.from_bytes(bytes(reply), 'big')

        version = register(0x08)
        if version & 0xFFF0 != 0x0010:
            raise RuntimeError('Unexpected MAX1704x version: ' + hex(version))
        voltage, percent, rate = decode(register(0x02), register(0x04), register(0x16))
        if not 2.5 <= voltage <= 4.3 or not 0 <= percent <= 110:
            raise RuntimeError('Implausible single-cell readings; check wiring and battery voltage.')
        return {'voltage_V': round(voltage, 3), 'battery_percent_estimate': round(percent, 1),
                'estimated_change_percent_per_hour': round(rate, 2),
                'trend': 'rising' if rate > 0.5 else 'falling' if rate < -0.5 else 'steady/uncertain',
                'charging_current_measured': False}
    finally:
        os.close(fd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bus', type=int, default=30)
    args = parser.parse_args()
    if args.bus < 0:
        parser.error('Bus must be nonnegative')
    try:
        print(json.dumps(read_battery(args.bus), indent=2))
    except (OSError, RuntimeError) as error:
        print('Battery gauge unavailable: ' + str(error), file=sys.stderr)
        sys.exit(1)
