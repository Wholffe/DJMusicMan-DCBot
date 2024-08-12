# DJ Music Man - The Discord Music Bot

## Description

DJ Music Man is a simple Discord bot designed for playing music in voice channels. It leverages `yt-dlp` to fetch audio streams from YouTube and `FFmpeg` to play the audio in Discord. The bot supports basic music control commands such as playing, skipping, and queue management, making it easy to enjoy music with friends directly in your Discord server.

## Requirements
- A Discord bot token [Creating a discord bot & getting a token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)
- Docker (recommended) [Docker's official website](https://www.docker.com/).

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

### Installation via Docker (recommended)
3. **Execute Docker Run Script**

   - ***Linux***
     - Run the script located at [start-and-update-djmusicman.sh](../scripts/linux/start-and-update-djmusicman.sh).

   - ***Windows***
     - Run the script located at [start-and-update-djmusicman.ps1](../scripts/windows/start-and-update-djmusicman.ps1).

   ***Note: Alternative Manual Container Run***

   - Manually start the Docker container from the root directory using the `.env` file:
   
     ```bash
     docker run -d --name djmusicman --env-file .env --restart unless-stopped "djmusicman"
     ```

### OR

### Installation Without Docker
   - Additional requirements for local run:
      - Python 3.8 or higher
      - `FFmpeg` for audio streaming

3. **Install the Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Bot in root dir**
   ```bash
   python main.py
   ```
   
## Contribution

Contributions to this repository are welcome! If you have additional ideas or improvements, feel free to submit pull requests.

## License

This repository is licensed under the [MIT License](../LICENSE).