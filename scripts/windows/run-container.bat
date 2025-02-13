@echo off

for /f "tokens=1,2 delims==" %%i in (../../.env) do (
    if "%%i"=="DISCORD_TOKEN" set DISCORD_TOKEN=%%j
)

docker pull ghcr.io/your_github_username/djmusicman-dcbot:latest
docker run -e DISCORD_TOKEN=%DISCORD_TOKEN% ghcr.io/your_github_username/djmusicman-dcbot:latest