#!/usr/bin/env bash

set -e

service="$1"

if [ "$service" != "" ]; then
  echo "Building specified library: $service"
  rm -rf "$service"/__pycache__
  docker compose build "$service" --no-cache
  echo "$service built!"
fi