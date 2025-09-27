# DJ Music Man - A Discord Music Bot

## Description

DJ Music Man is a Discord bot designed for playing music in voice channels. It leverages `yt-dlp` to fetch audio streams from YouTube and `FFmpeg` to play them in Discord. The bot is built to be stable and easy to deploy using Docker.

It supports essential music control commands such as playing, skipping, and queue management, making it easy to enjoy music with your friends directly on your Discord server.

## Requirements
- A Discord bot token [How to create a bot & get a token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)
- Docker (recommended) [Docker's official website](https://www.docker.com/)

## Setup and Installation

### 1️ Clone the Repository
```bash
git clone https://github.com/Wholffe/DJMusicMan-DCBot.git
cd DJMusicMan-DCBot
```

### 2️ Create the Configuration File (.env)
Create a `.env` file in the root of the project directory:
```dotenv
# --- Required ---
DISCORD_TOKEN=your-discord-bot-token-goes-here

# --- Optional ---
MAX_CACHE_FILES=100
IDLE_TIMER=180
```
Replace `your-discord-bot-token-goes-here` with your actual token.

### 3️ Add YouTube Cookies (Optional)
For playing age-restricted or members-only videos, the bot needs access to a YouTube account's cookies. This step is optional for public videos.  
[How to Add YouTube Cookies](add_yt_cookies.md)

### 4️ Run the Bot
**With Docker (Recommended)**

  **Windows (PowerShell):**
  ```powershell
  .\scripts\windows\run-container.ps1
  ```

  **Linux/macOS:**
  ```bash
  chmod +x ./scripts/linux/run-container.sh
  ./scripts/linux/run-container.sh
  ```

  These scripts will:
  - Stop and remove any old container
  - Build a fresh Docker image
  - Start the container with the correct settings, mounting the data directory for persistent caching and mapping your `.env` file

  #### Manual Docker Run (Alternative)
  ```bash
  docker run -d \
    --name djmusicman \
    --env-file .env \
    -v "$(pwd)/cache:/app/cache" \
    --restart unless-stopped \
    djmusicman
  ```

**Without Docker**

  For instructions on running the bot without Docker, see the separate file: [Manual Installation Steps](dj_music_man_manual_installation.md)

## Contribution

Contributions are welcome! If you have ideas for improvements or new features, feel free to open an issue or submit a pull request.

## License

This project is licensed under the [MIT License](../LICENSE).