FROM python:3.11-slim

LABEL org.opencontainers.image.title="verification-service" \
    org.opencontainers.image.description="Base Docker image for BioCompose REST API management, job processing, and datastorage with MongoDB, ensuring scalable and robust performance." \
    org.opencontainers.image.url="https://biosimulators.org/" \
    org.opencontainers.image.source="https://github.com/biosimulators/verification-server" \
    org.opencontainers.image.authors="Alexander Patrie <apatrie@uchc.edu>, BioSimulators Team <info@biosimulators.org>" \
    org.opencontainers.image.vendor="BioSimulators Team"

SHELL ["/usr/bin/env", "bash", "-c"]

# shared env
ENV DEBIAN_FRONTEND=noninteractive \
    MONGO_URI="mongodb://mongodb/?retryWrites=true&w=majority&appName=verification-server" \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_NO_INTERACTION=1

# copy docker assets
COPY assets/docker/config/.biosimulations.json /.google/.bio-check.json
COPY assets/docker/config/.pys_usercfg.ini /Pysces/.pys_usercfg.ini
COPY assets/docker/config/.pys_usercfg.ini /root/Pysces/.pys_usercfg.ini

WORKDIR /app

COPY ./gateway /app/gateway
COPY ./worker /app/worker
COPY ./shared /app/shared
COPY pyproject.toml /app/pyproject.toml

RUN mkdir -p /Pysces \
    && mkdir -p /Pysces/psc \
    && mkdir -p /root/Pysces \
    && mkdir -p /root/Pysces/psc \
    && python -m pip install --upgrade pip \
    && python -m pip install poetry \
    && poetry lock \
    && poetry install

# expose gateway port
EXPOSE 3001
