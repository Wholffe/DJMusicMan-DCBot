#!/bin/bash

# === ADJUST THIS: Define the current project path ===
PROJECT_PATH="$HOME/DJMusicMan-DCBot"
CONTAINER_NAME="djmusicman"
IMAGE="ghcr.io/wholffe/djmusicman-dcbot:latest"

cd "$PROJECT_PATH"

export $(grep -v '^#' .env | xargs)

CACHE_PATH="$PROJECT_PATH/cache"

docker pull "$IMAGE"
docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker run -d \
  --name "$CONTAINER_NAME" \
  -e DISCORD_TOKEN=$DISCORD_TOKEN \
  -e MAX_CACHE_FILES=${MAX_CACHE_FILES:-100} \
  -e IDLE_TIMER=${IDLE_TIMER:-180} \
  -e CACHE_DIR=/app/cache \
  -v "$CACHE_PATH":/app/cache \
  --restart unless-stopped \
  $IMAGE
docker images --filter 'dangling=true' -q | xargs -r docker rmi -f