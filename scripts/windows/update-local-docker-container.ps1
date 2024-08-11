# This script is intended for PowerShell in Windows environments.
# It updates the repository, restarts Docker containers, and removes old Docker images.

$DOCKER_IMAGE_NAME = "djmusicman"

$SCRIPT_PATH = $PSScriptRoot
$ROOT_PATH = Join-Path -Path $SCRIPT_PATH -ChildPath "..\.."

$DOCKER_COMPOSE_FILE = Join-Path -Path $ROOT_PATH -ChildPath "docker-compose.yml"

Set-Location -Path $ROOT_PATH

git pull origin main --force

docker-compose -f $DOCKER_COMPOSE_FILE down
docker-compose -f $DOCKER_COMPOSE_FILE up --build -d
docker image prune -f

$images = docker images $DOCKER_IMAGE_NAME -q
if ($images) {
    docker rmi -f $images
}