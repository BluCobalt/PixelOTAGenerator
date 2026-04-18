FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget unzip\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY POG /app/POG

RUN mkdir /app/tools

RUN wget -O /app/tools/avbroot.zip https://github.com/chenxiaolong/avbroot/releases/download/v3.29.0/avbroot-3.29.0-x86_64-unknown-linux-gnu.zip
RUN unzip -j /app/tools/avbroot.zip avbroot -d /app/tools/

RUN wget -O /app/tools/custota.zip https://github.com/chenxiaolong/Custota/releases/download/v5.21/custota-tool-5.21-x86_64-unknown-linux-gnu.zip
RUN unzip -j /app/tools/custota.zip custota-tool -d /app/tools/

RUN wget -O /app/tools/magiskboot.zip https://github.com/topjohnwu/Magisk/releases/download/v30.6/Magisk-v30.6.apk
RUN unzip -j /app/tools/magiskboot.zip lib/x86_64/libmagiskboot.so -d /app/tools/ && mv /app/tools/libmagiskboot.so /app/tools/magiskboot && chmod +x /app/tools/magiskboot


RUN set -eux; \
    mkdir -p /usr/local/bin; \
    for f in avbroot magiskboot custota-tool; do \
      if [ -f "/app/tools/$f" ]; then \
        cp "/app/tools/$f" /usr/local/bin/; \
        chmod +x "/usr/local/bin/$f"; \
      fi; \
    done

RUN mkdir /app/output /app/temp

ENV PATH="/usr/local/bin:${PATH}"

CMD ["python3", "-m", "POG"]
