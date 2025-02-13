#!/bin/bash

export $(grep -v '^#' ../../.env | xargs)

docker pull ghcr.io/your_github_username/djmusicman-dcbot:latest
docker run -e DISCORD_TOKEN=$DISCORD_TOKEN ghcr.io/your_github_username/djmusicman-dcbot:latest