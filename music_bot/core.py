from discord.ext import commands

from .utils import cm_clear,cm_djhelp,cm_leave,cm_ping,cm_play,cm_showq,cm_skip,cm_toggle,cm_shuffle,cm_loop
from .music_queue import MusicQueue


class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.client = bot
        self.queue = MusicQueue()

    @commands.command()
    async def play(self, ctx, *, search) -> None:
        return await cm_play(self, ctx, search)

    @commands.command()
    async def skip(self, ctx) -> None:
        await cm_skip(ctx)

    @commands.command()
    async def ping(self, ctx) -> None:
        await cm_ping(ctx)

    @commands.command()
    async def djhelp(self, ctx) -> None:
        await cm_djhelp(ctx)

    @commands.command()
    async def clear(self, ctx) -> None:
        await cm_clear(self,ctx)

    @commands.command()
    async def showq(self, ctx) -> None:
        return await cm_showq(self,ctx)

    @commands.command()
    async def toggle(self, ctx) -> None:
        await cm_toggle(ctx)
    
    @commands.command()
    async def leave(self, ctx) -> None:
        await cm_leave(ctx)
    
    @commands.command()
    async def shuffle(self,ctx) -> None:
        await cm_shuffle(self,ctx)
    
    @commands.command()
    async def loop(self,ctx) -> None:
        await cm_loop(self,ctx)