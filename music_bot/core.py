from discord.ext import commands
from .utils import play_next, join_voice_channel, add_to_queue, handle_error, is_playing


class MusicBot(commands.Cog):

    def __init__(self, bot):
        self.client = bot
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search) -> None:
        try:
            await join_voice_channel(ctx)
            await add_to_queue(ctx, search, self.queue)
            if not await is_playing(ctx):
                await play_next(ctx, self.queue, self.client)
        except Exception as e:
            await handle_error(ctx, "playing the song", e)

    @commands.command()
    async def skip(self, ctx) -> None:
        try:
            if await is_playing(ctx):
                ctx.voice_client.stop()
                await ctx.send("Skipped the current song.")
        except Exception as e:
            await handle_error(ctx, "skipping the song", e)

    @commands.command()
    async def ping(self, ctx) -> None:
        await ctx.send('pong')

    @commands.command()
    async def djhelp(self, ctx) -> None:
        help_message = (
            'Available commands:\n'
            '/clear - Clear the current queue\n'
            '/ping - Ping the bot\n'
            '/play <search> - Play a song from YouTube\n'
            '/showq - Show the current queue\n'
            '/skip - Skip the current song\n'
            '/toggle - Toggle pause|continue playback\n'
        )
        await ctx.send(help_message)

    @commands.command()
    async def clear(self, ctx) -> None:
        try:
            self.queue.clear()
            await ctx.send("Queue cleared.")
        except Exception as e:
            await handle_error(ctx, "clearing the queue", e)

    @commands.command()
    async def showq(self, ctx) -> None:
        if not self.queue:
            await ctx.send("The queue is empty.")
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