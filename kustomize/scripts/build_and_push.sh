#!/bin/bash

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

for architecture in amd64 arm64; do

  for service in api worker; do

    tag="${architecture}_latest"
    platform="linux/${architecture}"
    dockerfile="${ROOT_DIR}/Dockerfile-${service}"
    image_name="ghcr.io/biosimulations/biosim-${service}:${tag}"

    docker build --platform=${platform} -f ${dockerfile} --tag ${image_name} "${ROOT_DIR}" \
      || { echo "Failed to build ${service} for platform ${platform}"; exit 1; }

    docker push ${image_name}  \
      || { echo "Failed to push ${service} for platform ${platform}"; exit 1; }

    echo "built and pushed service ${service} for platform ${platform}"
  done
done
