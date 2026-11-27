FROM mcr.microsoft.com/playwright:v1.56.1-noble@sha256:f1e7e01021efd65dd1a2c56064be399f3e4de00fd021ac561325f2bfbb2b837a
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DISPLAY=:0
RUN apt-get update && apt-get install -y --no-install-recommends python3-pip xvfb && rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/runtime && cd /opt/runtime && npm init -y && npm install --save-exact playwright@1.56.1 --no-audit --no-fund
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
RUN python3 -m pip install --break-system-packages --no-cache-dir --index-url ${PIP_INDEX_URL} numpy==2.2.6 Pillow==11.2.1
COPY . /tests/
RUN chmod +x /tests/test.sh && mkdir -p /app/out /logs/verifier && useradd -m browser
WORKDIR /tests
CMD ["/tests/test.sh"]
