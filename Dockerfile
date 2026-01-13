FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates wget unzip\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY POG /app/POG
COPY tools /app/tools

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

CMD ["python3", "-m", "POG", "/app/config.json"]
