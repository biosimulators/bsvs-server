#!/usr/bin/env bash

set -e

service="$1"

if [ "$service" != "" ]; then
  echo "Building specified library: $service"
  docker compose build "$service" --no-cache
  echo "$service built!"
fi