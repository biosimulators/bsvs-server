#!/usr/bin/env bash

set -e

service="$1"
no_cache="$2"  # pass as --no-cache

echo "Building specified library: $service"
rm -rf "$service"/__pycache__

docker compose build "$service" "$no_cache"

echo "$service built!"