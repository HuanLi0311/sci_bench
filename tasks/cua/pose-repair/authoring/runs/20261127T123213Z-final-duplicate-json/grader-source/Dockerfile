FROM mcr.microsoft.com/playwright:v1.56.1-noble@sha256:f1e7e01021efd65dd1a2c56064be399f3e4de00fd021ac561325f2bfbb2b837a
ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1
RUN sed -i 's|http://archive.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g; s|http://security.ubuntu.com/ubuntu/|http://mirrors.tuna.tsinghua.edu.cn/ubuntu/|g' /etc/apt/sources.list.d/ubuntu.sources && apt-get update && apt-get install -y --no-install-recommends python3 python3-numpy && rm -rf /var/lib/apt/lists/*
WORKDIR /tests
COPY . /tests
RUN mkdir -p /app/out /service-evidence /original /logs/verifier && cp -r /tests/original/. /original/ && chmod 700 /tests && chmod 755 /tests/test.sh
CMD ["sleep","infinity"]
