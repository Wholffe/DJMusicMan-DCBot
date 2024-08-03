# DJ Music Man - The Discord Music Bot

## Description

DC Music Bot is a simple Discord bot designed for playing music in voice channels. It leverages `yt-dlp` to fetch audio streams from YouTube and `FFmpeg` to play the audio in Discord. The bot supports basic music control commands such as playing, skipping, and queue management, making it easy to enjoy music with friends directly in your Discord server.

## Requirements

- Python 3.8 or higher
- A Discord bot token
- `yt-dlp` for extracting audio from YouTube
- `FFmpeg` for audio streaming
- `discord.py` for interacting with Discord API
- `PyNaCl` for voice support

## Download and Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/Wholffe/DCMusicBot.git
   ```
2. **Install the Dependencies**
    ```bash
    pip install -r requirements.txt
    ```
3. **Set Up Environment Variables**
   - **Create a `.env` file in the root directory**:
   ```plaintext
   DISCORD_TOKEN=your-discord-token
   ```
-  Make sure to replace `your-discord-token` with your actual Discord bot token.

4. **Run the Bot in root dir**
   ```bash
    python main.py
   ```

## Contribution

Contributions to this repository are welcome! If you have additional ideas or improvements, feel free to submit pull requests.

## License

This repository is licensed under the MIT License.