$dockerImageName = "djmusicman"
$scriptPath = $PSScriptRoot
$rootPath = (Get-Item $scriptPath).parent.parent.FullName
$dataPath = Join-Path -Path $rootPath -ChildPath "data"

Set-Location -Path $rootPath

# git pull origin main --force

if (-not (Test-Path -Path $dataPath)) {
    New-Item -ItemType Directory -Path $dataPath
}

docker stop $dockerImageName
docker rm $dockerImageName

docker build -t $dockerImageName .
docker run -d `
    --name $dockerImageName `
    --env-file .env `
    -v "${dataPath}:/data" `
    --restart unless-stopped `
    $dockerImageName

docker image prune -f