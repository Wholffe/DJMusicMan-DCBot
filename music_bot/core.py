from discord.ext import commands

from .commands import (
    cm_clear,
    cm_clear_cache,
    cm_djhelp,
    cm_leave,
    cm_loop,
    cm_ping,
    cm_play,
    cm_playfirst,
    cm_remove,
    cm_restart,
    cm_showq,
    cm_shuffle,
    cm_skip,
    cm_toggle,
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
        self.client.remove_command("help")

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

    @commands.command()
    async def play(self, ctx, *, search: str) -> None:
        await cm_play(self, ctx, search)

    @commands.command()
    async def skip(self, ctx) -> None:
        await cm_skip(self, ctx)

    @commands.command()
    async def ping(self, ctx) -> None:
        await cm_ping(ctx)

    @commands.command(aliases=["djhelp"])
    async def help(self, ctx) -> None:
        await cm_djhelp(ctx)

    @commands.command()
    async def clear(self, ctx) -> None:
        await cm_clear(self, ctx)

    @commands.command(aliases=["queue"])
    async def showq(self, ctx) -> None:
        await cm_showq(self, ctx)

    @commands.command(aliases=["pause"])
    async def toggle(self, ctx) -> None:
        await cm_toggle(ctx)

    @commands.command()
    async def leave(self, ctx) -> None:
        await cm_leave(ctx)

    @commands.command()
    async def shuffle(self, ctx) -> None:
        await cm_shuffle(self, ctx)

    @commands.command()
    async def loop(self, ctx) -> None:
        await cm_loop(self, ctx)

    @commands.command(name="rm")
    async def remove_element(self, ctx, index: int) -> None:
        await cm_remove(self, ctx, index)

    @commands.command()
    async def playfirst(self, ctx, *, search: str) -> None:
        await cm_playfirst(self, ctx, search)

    @commands.command(aliases=["reset"])
    async def restart(self, ctx) -> None:
        await cm_restart(self, ctx)

    @commands.command()
    async def clear_cache(self, ctx) -> None:
        await cm_clear_cache(ctx)
