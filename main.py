import asyncio
import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

from musicbot import MusicBot

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

client = commands.Bot(command_prefix='/', intents=intents)


async def main():
  await client.add_cog(MusicBot(client))
  load_dotenv()
  DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
  await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
  asyncio.run(main())
