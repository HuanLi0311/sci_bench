#!/bin/bash
set -e
Xvfb :1 -screen 0 1920x1080x24 &
DISPLAY=:1 dbus-launch startxfce4 &
DISPLAY=:1 x11vnc -forever -shared -nopw -rfbport 5900 &
exec blender /app/materials/fighters.blend
