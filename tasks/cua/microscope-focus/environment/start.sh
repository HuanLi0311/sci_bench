#!/bin/bash
set -euo pipefail
Xvfb :0 -screen 0 1920x1080x24 -ac &
for attempt in $(seq 1 50); do test -S /tmp/.X11-unix/X0 && break; sleep 0.1; done
dbus-run-session -- startxfce4 >/tmp/xfce.log 2>&1 &
x11vnc -display :0 -forever -shared -nopw -rfbport 5900 >/tmp/vnc.log 2>&1 &
websockify --web=/usr/share/novnc 6080 localhost:5900 >/tmp/novnc.log 2>&1 &
python3 -m http.server 8080 --bind 0.0.0.0 --directory /app/materials >/tmp/server.log 2>&1 &
node --input-type=module -e 'import {chromium} from "/opt/runtime/node_modules/playwright/index.mjs"; const b=await chromium.launch({headless:false,args:["--no-sandbox","--start-maximized","--use-gl=angle","--use-angle=swiftshader","--enable-unsafe-swiftshader"]}); const p=await b.newPage({viewport:null}); await p.goto("http://127.0.0.1:8080/starter/"); await new Promise(()=>{});'
