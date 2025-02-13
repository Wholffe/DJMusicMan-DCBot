#!/bin/bash

# === ADJUST THIS: Define the current project path ===
PROJECT_PATH="$HOME/DJMusicMan-DCBot"
CONTAINER_NAME="djmusicman"
IMAGE="ghcr.io/wholffe/djmusicman-dcbot:latest"

cd "$PROJECT_PATH"

export $(grep -v '^#' .env | xargs)

docker pull "$IMAGE"
docker stop "$CONTAINER_NAME" || true
docker rm "$CONTAINER_NAME" || true
docker run -d --name "$CONTAINER_NAME" -e DISCORD_TOKEN=$DISCORD_TOKEN --restart unless-stopped $IMAGE
docker images --filter 'dangling=true' -q | xargs -r docker rmi -f