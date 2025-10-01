import asyncio
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from music_bot.core import MusicBot

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

client = commands.Bot(command_prefix="/", intents=intents)


async def main():
    await client.add_cog(MusicBot(client))
    load_dotenv()
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if DISCORD_TOKEN is None:
        raise ValueError("DISCORD_TOKEN environment variable not set.")
    await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
