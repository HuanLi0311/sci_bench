FROM mcr.microsoft.com/playwright:v1.56.1-noble@sha256:f1e7e01021efd65dd1a2c56064be399f3e4de00fd021ac561325f2bfbb2b837a
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 DISPLAY=:0
RUN apt-get update && apt-get install -y --no-install-recommends xfce4 xfce4-terminal x11vnc novnc websockify imagemagick webp python3 && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/runtime && cd /opt/runtime && npm init -y && npm install --save-exact three@0.169.0 playwright@1.56.1 --no-audit --no-fund
COPY materials/ /app/materials/
COPY start.sh /usr/local/bin/start-microscope
RUN mkdir -p /app/out /app/materials/starter/vendor && cp /opt/runtime/node_modules/three/build/three.module.js /app/materials/starter/vendor/ && cp /opt/runtime/node_modules/three/examples/jsm/controls/OrbitControls.js /app/materials/starter/vendor/ && cp /opt/runtime/node_modules/three/LICENSE /app/materials/starter/vendor/THREE-LICENSE.txt && chmod +x /usr/local/bin/start-microscope
WORKDIR /app
EXPOSE 8080 6080 5900
CMD ["/usr/local/bin/start-microscope"]
