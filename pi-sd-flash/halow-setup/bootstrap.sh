#!/bin/sh
set -eu
mount -o remount,rw /
mount -o remount,rw /boot/firmware
exec /usr/bin/python3 /boot/firmware/halow-setup/setup.py bootstrap
