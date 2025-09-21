$DOCKER_IMAGE_NAME = "djmusicman"
$SCRIPT_PATH = $PSScriptRoot
$ROOT_PATH = Join-Path -Path $SCRIPT_PATH -ChildPath "..\.."
$cachePath = "$ROOT_PATH\cache"

Set-Location -Path $ROOT_PATH

git pull origin main --force

docker stop $DOCKER_IMAGE_NAME
docker rm $DOCKER_IMAGE_NAME
docker build -t $DOCKER_IMAGE_NAME .
docker run -d `
    --name $DOCKER_IMAGE_NAME `
    --env-file .env `
    -e MAX_CACHE_FILES=${env:MAX_CACHE_FILES} `
    -e IDLE_TIMER=${env:IDLE_TIMER} `
    -v "${cachePath}:/app/cache" `
    --restart unless-stopped `
    $DOCKER_IMAGE_NAME

docker image prune -f