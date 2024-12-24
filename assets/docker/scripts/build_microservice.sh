#!/usr/bin/env bash

set -e

service="$1"

echo "Building specified library: $service"
rm -rf "$service"/__pycache__

docker compose build "$service"

echo "$service built!"