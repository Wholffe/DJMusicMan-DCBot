#!/bin/bash

# === ADJUST THIS: Define the current project path ===
PROJECT_PATH="$HOME/DJMusicMan-DCBot"
CONTAINER_NAME="djmusicman"
DOCKER_IMAGE_NAME="djmusicman"

cd "$PROJECT_PATH" && git pull origin main --force

sudo docker stop "$CONTAINER_NAME" || true
sudo docker rm "$CONTAINER_NAME" || true
sudo docker build -t "$DOCKER_IMAGE_NAME" .
sudo docker run -d --name "$CONTAINER_NAME" --env-file .env --restart unless-stopped "$DOCKER_IMAGE_NAME"

sudo docker images --filter 'dangling=true' -q | xargs -r sudo docker rmi -f