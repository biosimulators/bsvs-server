#!/usr/bin/env bash

set -e

docker system prune -a -f

# build api
./assets/docker/scripts/build_microservice.sh gateway

# deploy api
./assets/docker/scripts/deploy_microservice.sh gateway

# build worker
./assets/docker/scripts/build_microservice.sh worker

# deploy worker
./assets/docker/scripts/deploy_microservice.sh worker