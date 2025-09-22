#!/bin/bash

PROJECT_PATH=$(pwd)
CONTAINER_NAME="djmusicman"
DOCKER_IMAGE_NAME="djmusicman"
CACHE_PATH="$PROJECT_PATH/cache"

git pull origin main --force

mkdir -p "$CACHE_PATH"
chmod 777 "$CACHE_PATH"

sudo docker stop "$CONTAINER_NAME" || true
sudo docker rm "$CONTAINER_NAME" || true
sudo docker build -t "$DOCKER_IMAGE_NAME" .
sudo docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -v "$CACHE_PATH":/app/cache \
  --restart unless-stopped \
  "$DOCKER_IMAGE_NAME"

sudo docker images --filter 'dangling=true' -q | xargs -r sudo docker rmi -f