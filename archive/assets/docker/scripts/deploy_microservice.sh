#!/usr/bin/env bash

set -e

service="$1"
version="$2"
# gh_username="$3"
explicit_version=1

if [ "$version" == "" ]; then
  version=$(cat "$service"/.VERSION)
  explicit_version=0
fi

IMG_NAME=ghcr.io/biosimulators/bsvs-server-"$service":"$version"

# push version to GHCR
docker push "$IMG_NAME"

# push newest latest to GHCR
docker tag "$IMG_NAME" ghcr.io/biosimulators/bsvs-server-"$service":latest
docker push ghcr.io/biosimulators/bsvs-server-"$service":latest

# handle version
VERSION_FILE=./"$service"/.VERSION

if [ "$explicit_version" == 1 ]; then
  echo "Updating internal version of $service with specified version."
  echo "$version" > "$VERSION_FILE"
fi

echo "Updated version: $version"
