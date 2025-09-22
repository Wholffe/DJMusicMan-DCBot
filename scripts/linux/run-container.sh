#!/bin/bash

PROJECT_PATH=$(pwd)
CONTAINER_NAME="djmusicman"
IMAGE="ghcr.io/wholffe/djmusicman-dcbot:latest"
CACHE_PATH="$PROJECT_PATH/cache"

mkdir -p "$CACHE_PATH"
chmod 777 "$CACHE_PATH"

docker pull "$IMAGE"
docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "$CACHE_PATH":/app/cache \
  --restart unless-stopped \
  "$IMAGE"

docker image prune -f