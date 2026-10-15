import asyncio
import os

import discord
from discord import app_commands
from discord.ext import commands

from music_bot.config import GUILD_ID
from music_bot.core import MusicBot
from music_bot.logger import logger

intents = discord.Intents.default()
intents.voice_states = True


class DJMusicMan(commands.Bot):
    """Bot that loads the music cog and registers its slash commands."""

    async def setup_hook(self) -> None:
        """Loads the cog and registers the slash commands with Discord."""
        await self.add_cog(MusicBot(self))
        # Runs once at startup, unlike on_ready, which repeats on reconnects
        try:
            if GUILD_ID:
                guild = discord.Object(id=GUILD_ID)
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
            else:
                synced = await self.tree.sync()
        except discord.HTTPException:
            # Commands from an earlier sync keep working, so the bot keeps running
            logger.error("Failed to sync slash commands", exc_info=True)
            return
        logger.info(f"Synced {len(synced)} slash commands")

    async def on_message(self, message: discord.Message) -> None:
        """Ignores messages, the bot only has slash commands."""


client = DJMusicMan(
    command_prefix=commands.when_mentioned,
    help_command=None,
    intents=intents,
    allowed_contexts=app_commands.AppCommandContext(guild=True),
)


async def main() -> None:
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if DISCORD_TOKEN is None:
        raise ValueError("DISCORD_TOKEN environment variable not set.")
    await client.start(DISCORD_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
