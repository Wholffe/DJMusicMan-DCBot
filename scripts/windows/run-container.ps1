$containerName = "djmusicman"
$cachePath = "$PWD\cache"

$envVars = Get-Content -Path ".env" | ForEach-Object {
    $name, $value = $_ -split '='
    [PSCustomObject]@{ Name = $name; Value = $value }
}

foreach ($envVar in $envVars) {
    if ($envVar.Name -eq "DISCORD_TOKEN") {
        $env:DISCORD_TOKEN = $envVar.Value
    }
    if ($envVar.Name -eq "MAX_CACHE_FILES") {
        $env:MAX_CACHE_FILES = $envVar.Value
    }
    if ($envVar.Name -eq "IDLE_TIMER") {
        $env:IDLE_TIMER = $envVar.Value
    }
}

docker pull ghcr.io/wholffe/djmusicman-dcbot:latest
docker run --name $containerName `
    -e DISCORD_TOKEN=$env:DISCORD_TOKEN `
    -e MAX_CACHE_FILES=${env:MAX_CACHE_FILES} `
    -e IDLE_TIMER=${env:IDLE_TIMER} `
    -v "${cachePath}:/app/cache" `
    ghcr.io/wholffe/djmusicman-dcbot:latest