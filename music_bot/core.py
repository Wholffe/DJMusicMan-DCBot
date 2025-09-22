from discord.ext import commands

from .music_queue import MusicQueue
from .utils import (
    cm_clear,
    cm_clear_cache,
    cm_djhelp,
    cm_leave,
    cm_loop,
    cm_ping,
    cm_play,
    cm_playfirst,
    cm_remove,
    cm_reset,
    cm_showq,
    cm_shuffle,
    cm_skip,
    cm_toggle,
)


class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.client = bot
        self.queue = MusicQueue()
        self.client.remove_command("help")

    @commands.command()
    async def play(self, ctx, *, search) -> None:
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
    async def playfirst(self, ctx, *, search) -> None:
        await cm_playfirst(self, ctx, search)

    @commands.command()
    async def reset(self, ctx) -> None:
        await cm_reset(self, ctx)

    @commands.command()
    async def clear_cache(self, ctx) -> None:
        await cm_clear_cache(ctx)
