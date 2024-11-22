from discord.ext import commands

from .utils import cm_clear,cm_djhelp,cm_leave,cm_ping,cm_play,cm_showq,cm_skip,cm_toggle
from .utils import error_handling


class MusicBot(commands.Cog):

    def __init__(self, bot):
        self.client = bot
        self.queue = []

    @commands.command(name='play')
    @error_handling
    async def play(self, ctx, *, search) -> None:
        await cm_play(self, ctx, search)

    @commands.command(name='skip')
    @error_handling
    async def skip(self, ctx) -> None:
        await cm_skip(ctx)

    @commands.command(name='ping')
    @error_handling
    async def ping(self, ctx) -> None:
        await cm_ping(ctx)

    @commands.command(name='djhelp')
    @error_handling
    async def djhelp(self, ctx) -> None:
        await cm_djhelp(ctx)

    @commands.command(name='clear')
    @error_handling
    async def clear(self, ctx) -> None:
        await cm_clear(self,ctx)

    @commands.command(name='showq')
    @error_handling
    async def showq(self, ctx) -> None:
        await cm_showq(self,ctx)

    @commands.command(name='toggle')
    @error_handling
    async def toggle(self, ctx) -> None:
        await cm_toggle(ctx)
    
    @commands.command(name='leave')
    @error_handling
    async def leave(self, ctx) -> None:
        await cm_leave(ctx)