# DJ Music Man - The Discord Music Bot

## Description

DJ Music Man is a simple Discord bot designed for playing music in voice channels. It leverages `yt-dlp` to fetch audio streams from YouTube and `FFmpeg` to play the audio in Discord. The bot supports basic music control commands such as playing, skipping, and queue management, making it easy to enjoy music with friends directly in your Discord server.

## Requirements

- Python 3.8 or higher
- A Discord bot token
- `FFmpeg` for audio streaming
- `PyNaCl` for voice support

## Download and Installation
1. **Clone the Repository and Navigate to the Repository Directory**
   ```bash
   git clone https://github.com/Wholffe/DCMusicBot.git
   ```

2. **Set Up Environment Variables**
   - Create a `.env` file in the root directory:
   ```plaintext
   DISCORD_TOKEN=your-discord-token
   ```
   - Make sure to replace `your-discord-token` with your actual Discord bot token.

### Installation via Docker
   Ensure Docker is Installed on your machine. Download and install [Docker](https://www.docker.com/)

3. **Build the Docker Image with the docker-compose file**
   ```bash
   docker-compose up --build -d
   ```

Note: **Rebuild the Image and Restart the Container**
   - After making changes to your code or configuration, it's important to stop and remove the existing containers, rebuild the Docker image to incorporate these changes, and restart the container to ensure the latest version is running.

   Update local Docker Container
   - Linux
     - [update-local-docker-containers](../scripts/linux/update-local-docker-container.sh).
   - Windows
     - [update-local-docker-container](../scripts/windows/update-local-docker-container.ps1).

### Installation Without Docker

3. **Install the Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Bot in root dir**
   ```bash
    python main.py
   ```

###

## Contribution

Contributions to this repository are welcome! If you have additional ideas or improvements, feel free to submit pull requests.

## License

This repository is licensed under the [MIT License](../LICENSE).