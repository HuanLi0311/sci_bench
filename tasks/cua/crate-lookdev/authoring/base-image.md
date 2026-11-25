# Base image: `blender-bench:gui`

The task builds on the local Blender desktop image. This file records how it
was made, because the official Blender tarball is unreachable from this
network (`download.blender.org` and its mirrors answer 403 or serve an HTML
error page) and a fresh clone of this repo on another machine has to rebuild it
before the task can be built.

```
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive PYTHONIOENCODING=utf-8

# apt via a mirror that works here
RUN sed -i 's@//.*archive.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g; \
            s@//security.ubuntu.com@//mirrors.tuna.tsinghua.edu.cn@g' \
        /etc/apt/sources.list.d/ubuntu.sources \
 && apt-get update && apt-get install -y --no-install-recommends \
        libx11-6 libxi6 libxxf86vm1 libxfixes3 libxrender1 libgl1 libglu1-mesa \
        libxkbcommon0 libsm6 libice6 libegl1 libgomp1 libsndfile1 libopenal1 \
        libfontconfig1 libfreetype6 libdbus-1-3 libxrandr2 libxinerama1 \
        libxcursor1 libasound2t64 libpulse0 libwayland-client0 libdecor-0-0 \
        ffmpeg python3 ca-certificates xz-utils \
 && rm -rf /var/lib/apt/lists/*

# Blender 4.2.3 LTS, official linux-x64 build, pre-downloaded into the context
COPY blender-4.2.3-linux-x64.tar.xz /tmp/
RUN tar -xf /tmp/blender-4.2.3-linux-x64.tar.xz -C /opt \
 && mv /opt/blender-4.2.3-linux-x64 /opt/blender \
 && ln -s /opt/blender/blender /usr/local/bin/blender \
 && rm /tmp/blender-4.2.3-linux-x64.tar.xz

# desktop stack
RUN apt-get update && apt-get install -y --no-install-recommends \
        xvfb xfce4 xfce4-terminal dbus-x11 x11vnc x11-utils x11-xserver-utils \
        libgl1-mesa-dri libglx-mesa0 mesa-utils scrot xdotool wmctrl time \
        fonts-noto-cjk fonts-dejavu-core \
 && rm -rf /var/lib/apt/lists/*

# entrypoint runs /usr/local/bin/start-desktop, then execs CMD
ENV DISPLAY=:1 LIBGL_ALWAYS_SOFTWARE=1 XDG_RUNTIME_DIR=/tmp/runtime-root
COPY entrypoint start-desktop /usr/local/bin/
CMD ["sleep", "infinity"]
```

`start-desktop` starts `Xvfb :1` at 1920×1080 with GLX, `xfce4-session`, disables
compositing and screen blanking, and starts `x11vnc` on 5900. The harbor
`computer-1` agent checks for `/tmp/.X11-unix/X1` and reuses the display if it
is already up.

## Seen in this task

- The environment image layers on top of it: `imagemagick` (for the agent's
  screenshot `import`) and `webp` (for `cwebp`) are missing from the base.
- The verifier image uses the same base so both sides render with one binary.
