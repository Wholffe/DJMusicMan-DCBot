$containerName = "djmusicman"
$image = "ghcr.io/wholffe/djmusicman-dcbot:latest"

$scriptPath = $PSScriptRoot
$cachePath = Join-Path -Path $scriptPath -ChildPath "cache"

if (-not (Test-Path -Path $cachePath)) {
    New-Item -ItemType Directory -Path $cachePath
}

docker pull $image

docker stop $containerName -ErrorAction SilentlyContinue
docker rm $containerName -ErrorAction SilentlyContinue

docker run -d `
    --name $containerName `
    --env-file .env `
    -v "${cachePath}:/app/cache" `
    --restart unless-stopped `
    $image

docker image prune -f