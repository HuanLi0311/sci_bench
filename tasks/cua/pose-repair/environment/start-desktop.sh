#!/bin/bash
set -e
Xvfb :1 -screen 0 1920x1080x24 &
DISPLAY=:1 dbus-launch startxfce4 &
DISPLAY=:1 x11vnc -forever -shared -nopw -rfbport 5900 &
node /app/web.cjs &
exec /ms-playwright/chromium-1194/chrome-linux/chrome --no-sandbox --test-type --no-first-run --start-maximized --remote-debugging-port=9222 --use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader http://localhost:8080
