FROM python:3.11-slim

LABEL org.opencontainers.image.title="bio-compose-server-base" \
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

# cd /app
WORKDIR /app

ARG CONTENT_DIR
COPY ./$CONTENT_DIR /app/$CONTENT_DIR
# COPY ./gateway /app/gateway
# COPY ./worker /app/worker

RUN mkdir -p /Pysces \
    && mkdir -p /Pysces/psc \
    && mkdir -p /root/Pysces \
    && mkdir -p /root/Pysces/psc \
    &&


# to run with a local network:
# net=app-net
# docker network create "$net"
# docker run -d --rm --name "$lib" --net "$net" --platform linux/amd64 "$PKG_ROOT"-"$lib":latest
# docker run -it --name "$lib" --net "$net" --platform linux/amd64 "$PKG_ROOT"-"$lib"

# # create conda env from yml and ensure env activation
# RUN conda env create -f config/environment.base.yml -y \
#     && rm -f config/environment.base.yml \
#     && conda env export --no-builds > config/environment.lock.yml \
#     && poetry lock

# create lockfile conda analogy: conda env export --no-builds > environment.lock.yml
# && conda create -n conda-env python=3.10 -y \
# && poetry install --without=api,worker,composition \
# && poetry config virtualenvs.in-project true \