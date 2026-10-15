import discord
from discord import app_commands
from discord.ext import commands

from .commands import (
    cm_clear,
    cm_clear_cache,
    cm_help,
    cm_leave,
    cm_loop,
    cm_pause,
    cm_ping,
    cm_play,
    cm_playfirst,
    cm_queue,
    cm_remove,
    cm_restart,
    cm_shuffle,
    cm_skip,
)
from .config import STARTUP_CHANNEL_ID
from .constants import VERSION
from .logger import logger
from .music_queue import MusicQueue
from .services import message_handler


class MusicBot(commands.Cog):
    def __init__(self, bot) -> None:
        self.client = bot
        self.queue = MusicQueue()
        self.message_handler = message_handler

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        info_message = f"{self.client.user} is ready. Version: {VERSION}"
        logger.info(info_message)

        if not STARTUP_CHANNEL_ID:
            return
        channel = self.client.get_channel(STARTUP_CHANNEL_ID)
        if not channel:
            logger.warning(f"Channel ID {STARTUP_CHANNEL_ID} not found.")
            return
        await self.message_handler.send_info(channel, info_message)

    @app_commands.command()
    @app_commands.describe(search="YouTube link, playlist or search terms")
    async def play(self, interaction: discord.Interaction, search: str) -> None:
        """Plays a song or playlist from YouTube."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_play(self, ctx, search)

    @app_commands.command()
    async def skip(self, interaction: discord.Interaction) -> None:
        """Skips the current song."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_skip(self, ctx)

    @app_commands.command()
    async def ping(self, interaction: discord.Interaction) -> None:
        """Shows the bot's latency."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_ping(ctx)

    @app_commands.command()
    async def help(self, interaction: discord.Interaction) -> None:
        """Shows all commands."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_help(ctx)

    @app_commands.command()
    async def clear(self, interaction: discord.Interaction) -> None:
        """Clears the queue."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_clear(self, ctx)

    @app_commands.command(name="queue")
    async def show_queue(self, interaction: discord.Interaction) -> None:
        """Shows the current queue."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_queue(self, ctx)

    @app_commands.command()
    async def pause(self, interaction: discord.Interaction) -> None:
        """Pauses or resumes playback."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_pause(ctx)

    @app_commands.command()
    async def leave(self, interaction: discord.Interaction) -> None:
        """Disconnects the bot from the voice channel."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_leave(ctx)

    @app_commands.command()
    async def shuffle(self, interaction: discord.Interaction) -> None:
        """Shuffles the queue."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_shuffle(self, ctx)

    @app_commands.command()
    async def loop(self, interaction: discord.Interaction) -> None:
        """Toggles looping of the current song."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_loop(self, ctx)

    @app_commands.command()
    @app_commands.describe(position="Position in the queue (see /queue)")
    async def remove(self, interaction: discord.Interaction, position: int) -> None:
        """Removes a song from the queue."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_remove(self, ctx, position)

    @app_commands.command()
    @app_commands.describe(search="YouTube link, playlist or search terms")
    async def playfirst(self, interaction: discord.Interaction, search: str) -> None:
        """Plays a song or playlist from YouTube before the rest of the queue."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_playfirst(self, ctx, search)

    @app_commands.command()
    async def restart(self, interaction: discord.Interaction) -> None:
        """Restarts the bot."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_restart(self, ctx)

    @app_commands.command()
    async def clear_cache(self, interaction: discord.Interaction) -> None:
        """Clears the song cache."""
        ctx = await commands.Context.from_interaction(interaction)
        await cm_clear_cache(ctx)
