FROM mcr.microsoft.com/playwright:v1.56.1-noble@sha256:f1e7e01021efd65dd1a2c56064be399f3e4de00fd021ac561325f2bfbb2b837a
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g; s|http://security.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources && apt-get update && apt-get install -y --no-install-recommends python3 curl xvfb xfce4 dbus-x11 x11vnc imagemagick webp && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY materials/ /app/materials/
COPY web.cjs /app/web.cjs
COPY start-desktop.sh /usr/local/bin/start-desktop
COPY entrypoint.sh /usr/local/bin/task-entrypoint
RUN mkdir /app/out && chmod 755 /usr/local/bin/start-desktop /usr/local/bin/task-entrypoint
ENV DISPLAY=:1 POSE_SERVICE=http://pose-service:8090
ENTRYPOINT ["/usr/local/bin/task-entrypoint"]
CMD ["sleep","infinity"]
