$dockerImageName = "djmusicman"
$scriptPath = $PSScriptRoot
$rootPath = (Get-Item $scriptPath).parent.parent.FullName
$cachePath = Join-Path -Path $rootPath -ChildPath "cache"

Set-Location -Path $rootPath

# git pull origin main --force

if (-not (Test-Path -Path $cachePath)) {
    New-Item -ItemType Directory -Path $cachePath
}

docker stop $dockerImageName
docker rm $dockerImageName

docker build -t $dockerImageName .
docker run -d `
    --name $dockerImageName `
    --env-file .env `
    -v "${cachePath}:/app/cache" `
    --restart unless-stopped `
    $dockerImageName

docker image prune -f