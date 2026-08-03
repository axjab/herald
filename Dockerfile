
FROM python:3.12-slim

# Docker CLI (for docker exec/restart) + git (for pulling /scripts repo)
RUN apt-get update && apt-get install -y --no-install-recommends \
        docker.io \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --break-system-packages \
    nats-py \
    httpx

WORKDIR /app
COPY herald.py                     /app/herald.py
COPY scripts/entrypoint.sh         /usr/local/bin/entrypoint.sh
COPY scripts/sync-repository.sh    /usr/local/bin/sync-repository.sh
RUN chmod +x /usr/local/bin/*
# The repository which contains scripts Herald is supposed to trigger
RUN mkdir -p /scripts
# Extension point for custom executables
RUN mkdir -p /opt/bin
ENV PATH="/opt/bin:${PATH}"

# VOLUME ["/scripts"]

ENTRYPOINT ["entrypoint.sh"]
