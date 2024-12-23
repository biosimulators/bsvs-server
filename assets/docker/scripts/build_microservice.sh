#!/usr/bin/env bash

prune="$1"
service="$2"

if [ "$prune" == "-p" ]; then
  docker system prune -a -f
fi

# remove pycaches if exists
sudo rm -r "$service"/__pycache__

if [ "$service" != "" ]; then
  echo "Building specified library: $service"
  docker compose build "$service" --no-cache
  echo "$service built!"
fi