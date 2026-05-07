#!/bin/bash
# run.sh -- launcher for the kiosk app, called by the LXDE autostart entry.
# Logs all output to log.txt so you can debug from SSH if the screen is dead.

set -u

APPDIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APPDIR"

# Wait for the desktop session to settle and DISPLAY to be ready.
sleep 5

exec python3 "$APPDIR/myapp.py" >> "$APPDIR/log.txt" 2>&1
