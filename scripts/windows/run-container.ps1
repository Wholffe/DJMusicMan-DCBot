$containerName = "djmusicman"
$image = "ghcr.io/wholffe/djmusicman-dcbot:latest"

$scriptPath = $PSScriptRoot
$dataPath = Join-Path -Path $scriptPath -ChildPath "data"

if (-not (Test-Path -Path $dataPath)) {
    New-Item -ItemType Directory -Path $dataPath
}

docker pull $image

docker stop $containerName -ErrorAction SilentlyContinue
docker rm $containerName -ErrorAction SilentlyContinue

docker run -d `
    --name $containerName `
    --env-file .env `
    -v "${dataPath}:/data" `
    --restart unless-stopped `
    $image

docker image prune -f