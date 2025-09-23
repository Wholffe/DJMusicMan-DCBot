#!/bin/bash

PROJECT_PATH=$(pwd)
CONTAINER_NAME="djmusicman"
IMAGE="ghcr.io/wholffe/djmusicman-dcbot:latest"
DATA_PATH="$PROJECT_PATH/data"

mkdir -p "$DATA_PATH"
chmod 777 "$DATA_PATH"

docker pull "$IMAGE"
docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "$DATA_PATH":/data \
  --restart unless-stopped \
  "$IMAGE"

docker image prune -f