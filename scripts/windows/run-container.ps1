$containerName = "djmusicman"

$envVars = Get-Content -Path ".env" | ForEach-Object {
    $name, $value = $_ -split '='
    [PSCustomObject]@{ Name = $name; Value = $value }
}

foreach ($envVar in $envVars) {
    if ($envVar.Name -eq "DISCORD_TOKEN") {
        $env:DISCORD_TOKEN = $envVar.Value
    }
}

docker pull ghcr.io/wholffe/djmusicman-dcbot:latest
docker run --name $containerName -e DISCORD_TOKEN=$env:DISCORD_TOKEN ghcr.io/wholffe/djmusicman-dcbot:latest