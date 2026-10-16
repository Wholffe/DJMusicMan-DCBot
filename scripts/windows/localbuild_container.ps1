$dockerImageName = "djmusicman"
$scriptPath = $PSScriptRoot
$rootPath = (Get-Item $scriptPath).parent.parent.FullName
$dataPath = Join-Path -Path $rootPath -ChildPath "data"

Set-Location -Path $rootPath

# git pull origin main --force

if (-not (Test-Path -Path $dataPath)) {
    New-Item -ItemType Directory -Path $dataPath
}

docker build --build-arg CACHE_BUST="$(Get-Date -UFormat %s)" -t $dockerImageName .
if ($LASTEXITCODE -ne 0) { exit 1 }

docker stop $dockerImageName 2>$null
docker rm $dockerImageName 2>$null

docker run -d `
    --name $dockerImageName `
    --env-file .env `
    -v "${dataPath}:/data" `
    --restart unless-stopped `
    $dockerImageName

docker image prune -f