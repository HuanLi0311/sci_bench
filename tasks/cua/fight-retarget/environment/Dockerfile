FROM ubuntu:24.04@sha256:562111b88caa79c71391c0c4d3c2114a7d5c35915c20561fd893cb1e07929e6b
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g; s|http://security.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources && apt-get update && apt-get install -y --no-install-recommends     ca-certificates curl xz-utils libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1     libgl1 libegl1 libxkbcommon0 libsm6 python3 python3-numpy python3-pil ffmpeg     && rm -rf /var/lib/apt/lists/*
RUN curl -fL --retry 4 https://mirrors.ocf.berkeley.edu/blender/release/Blender4.2/blender-4.2.3-linux-x64.tar.xz -o /tmp/blender.tar.xz     && echo '3a64efd1982465395abab4259b4091d5c8c56054c7267e9633e4f702a71ea3f4  /tmp/blender.tar.xz' | sha256sum -c -     && tar -xJf /tmp/blender.tar.xz -C /opt && rm /tmp/blender.tar.xz     && ln -s /opt/blender-4.2.3-linux-x64/blender /usr/local/bin/blender
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g; s|http://security.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources && apt-get update && apt-get install -y --no-install-recommends xvfb xfce4 dbus-x11 x11vnc imagemagick webp xdotool && rm -rf /var/lib/apt/lists/*
RUN blender -b --factory-startup --python-expr "import bpy; bpy.context.preferences.view.show_splash=False; bpy.ops.wm.save_userpref()"
WORKDIR /app
COPY materials/ /app/materials/
COPY start-desktop.sh /usr/local/bin/start-desktop
COPY entrypoint.sh /usr/local/bin/task-entrypoint
RUN mkdir /app/out && chmod +x /usr/local/bin/start-desktop /usr/local/bin/task-entrypoint
ENV DISPLAY=:1
ENTRYPOINT ["/usr/local/bin/task-entrypoint"]
CMD ["sleep","infinity"]
