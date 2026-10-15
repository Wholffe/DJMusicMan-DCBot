$containerName = "djmusicman"
$image = "ghcr.io/wholffe/djmusicman-dcbot:latest"

$scriptPath = $PSScriptRoot
$rootPath = (Get-Item $scriptPath).parent.parent.FullName
$dataPath = Join-Path -Path $rootPath -ChildPath "data"

Set-Location -Path $rootPath

if (-not (Test-Path -Path $dataPath)) {
    New-Item -ItemType Directory -Path $dataPath
}

docker pull $image

docker stop $containerName 2>$null
docker rm $containerName 2>$null

docker run -d `
    --name $containerName `
    --env-file .env `
    -v "${dataPath}:/data" `
    --restart unless-stopped `
    $image

docker image prune -f