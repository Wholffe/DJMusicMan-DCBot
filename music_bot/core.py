from discord.ext import commands

from .utils import cm_clear,cm_djhelp,cm_leave,cm_ping,cm_play,cm_showq,cm_skip,cm_toggle,cm_shuffle,cm_loop,cm_remove
from .music_queue import MusicQueue


class MusicBot(commands.Cog):
    def __init__(self, bot):
        self.client = bot
        self.queue = MusicQueue()
        self.client.remove_command('help')

    @commands.command()
    async def play(self, ctx, *, search) -> None:
        return await cm_play(self, ctx, search)

    @commands.command()
    async def skip(self, ctx) -> None:
        await cm_skip(self,ctx)

    @commands.command()
    async def ping(self, ctx) -> None:
        await cm_ping(ctx)

    @commands.command(aliases=['djhelp'])
    async def help(self, ctx) -> None:
        await cm_djhelp(ctx)

    @commands.command()
    async def clear(self, ctx) -> None:
        await cm_clear(self,ctx)

    @commands.command()
    async def showq(self, ctx) -> None:
        return await cm_showq(self,ctx)

    @commands.command(aliases=['pause'])
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
    
    @commands.command(name='rm')
    async def remove_element(self,ctx,index:int) -> None:
        await cm_remove(self,ctx,index)