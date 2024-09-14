from discord.ext import commands

from .utils import play_next, join_voice_channel, add_to_queue, handle_error, is_playing
from music_bot import constants as CONST


class MusicBot(commands.Cog):

    def __init__(self, bot):
        self.client = bot
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search) -> None:
        try:
            if (not await join_voice_channel(ctx) or not await add_to_queue(ctx, search, self.queue)):
                return
            if not await is_playing(ctx):
                await play_next(ctx, self.queue, self.client)
        except Exception as e:
            await handle_error(ctx, CONST.ACTION_PLAYING_SONG, e)

    @commands.command()
    async def skip(self, ctx) -> None:
        try:
            if await is_playing(ctx):
                ctx.voice_client.stop()
                await ctx.send(CONST.MESSAGE_SKIPPED_SONG)
        except Exception as e:
            await handle_error(ctx, CONST.ACTION_SKIPPING_SONG, e)

    @commands.command()
    async def ping(self, ctx) -> None:
        await ctx.send(CONST.MESSAGE_PONG)

    @commands.command()
    async def djhelp(self, ctx) -> None:
        await ctx.send(CONST.MESSAGE_HELP)

    @commands.command()
    async def clear(self, ctx) -> None:
        try:
            self.queue.clear()
            await ctx.send(CONST.MESSEGE_QUEUE_CLEARED)
        except Exception as e:
            await handle_error(ctx, CONST.ACTION_CLEARING_QUEUE, e)

    @commands.command()
    async def showq(self, ctx) -> None:
        if not self.queue:
            await ctx.send(CONST.MESSAGE_QUEUE_EMPTY)
            return
        queue_list = ""
        for i, song in enumerate(self.queue):
            queue_list += f"{i+1}. {song[1]}\n"
        await ctx.send(f"Queue:\n{queue_list}")

    @commands.command()
    async def toggle(self, ctx) -> None:
        if await is_playing(ctx):
            await ctx.voice_client.pause()
        else:
            await ctx.voice_client.resume()