#!/bin/bash

PROJECT_PATH=$(pwd)
CONTAINER_NAME="djmusicman"
DOCKER_IMAGE_NAME="djmusicman"
DATA_PATH="$PROJECT_PATH/data"

#git pull origin main --force

mkdir -p "$DATA_PATH"
chmod 777 "$DATA_PATH"

docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker build --no-cache -t "$DOCKER_IMAGE_NAME" .
docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "$DATA_PATH":/data \
  --restart unless-stopped \
  "$DOCKER_IMAGE_NAME"

docker images --filter 'dangling=true' -q | xargs -r sudo docker rmi -f