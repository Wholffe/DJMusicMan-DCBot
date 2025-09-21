#!/bin/bash

# === ADJUST THIS: Define the current project path ===
PROJECT_PATH="$HOME/DJMusicMan-DCBot"
CONTAINER_NAME="djmusicman"
DOCKER_IMAGE_NAME="djmusicman"
CACHE_PATH="$PROJECT_PATH/cache"

cd "$PROJECT_PATH" && git pull origin main --force

sudo docker stop "$CONTAINER_NAME" || true
sudo docker rm "$CONTAINER_NAME" || true
sudo docker build -t "$DOCKER_IMAGE_NAME" .
sudo docker run -d \
  --name "$CONTAINER_NAME" \
  --env-file .env \
  -e MAX_CACHE_FILES=${MAX_CACHE_FILES:-100} \
  -e IDLE_TIMER=${IDLE_TIMER:-180} \
  -e CACHE_DIR=/app/cache \
  -v "$CACHE_PATH":/app/cache \
  --restart unless-stopped \
  "$DOCKER_IMAGE_NAME"

sudo docker images --filter 'dangling=true' -q | xargs -r sudo docker rmi -f