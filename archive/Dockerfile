FROM python:3.11-slim

LABEL org.opencontainers.image.title="bsvs-server" \
    org.opencontainers.image.description="Docker image for REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance." \
    org.opencontainers.image.url="https://biosimulators.org/" \
    org.opencontainers.image.source="https://github.com/biosimulators/bsvs-server" \
    org.opencontainers.image.authors="Alexander Patrie <apatrie@uchc.edu>, BioSimulators Team <info@biosimulators.org>" \
    org.opencontainers.image.vendor="BioSimulators Team"

SHELL ["/usr/bin/env", "bash", "-c"]

# shared env
ENV DEBIAN_FRONTEND=noninteractive \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_NO_INTERACTION=1

# copy docker assets
COPY archive/assets/docker/config/.biosimulations.json /.google/.bio-check.json
COPY assets/docker/config/.pys_usercfg.ini /Pysces/.pys_usercfg.ini
COPY assets/docker/config/.pys_usercfg.ini /root/Pysces/.pys_usercfg.ini

WORKDIR /app

COPY gateway /app/gateway
COPY worker /app/worker
COPY shared /app/shared
COPY ../pyproject.toml /app/pyproject.toml

RUN apt-get update \
    && apt-get install libexpat1 -y \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --upgrade pip \
    && python -m pip install poetry \
    && poetry lock \
    && poetry install

# expose gateway port
EXPOSE 3001
