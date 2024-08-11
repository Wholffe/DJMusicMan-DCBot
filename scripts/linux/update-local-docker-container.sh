# This script is intended for the command line in Linux environments for locally hosted containers.
# It updates the repository, restarts Docker containers, and removes old Docker images.

DOCKER_IMAGE_NAME="djmusicman"
PROJECT_PATH="/home/pi/DCMusicBot"

cd "$PROJECT_PATH" && \
git pull origin main --force && \
sudo docker-compose down && \
sudo docker-compose up --build -d && \
sudo docker images --filter 'dangling=true' -q | xargs sudo docker rmi -f && \
sudo docker images "$DOCKER_IMAGE_NAME" -q | xargs sudo docker rmi -f