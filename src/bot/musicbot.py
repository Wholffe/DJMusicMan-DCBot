from discord.ext import commands

from .musicbot_utils import add_to_queue, join_voice_channel, play_next


class MusicBot(commands.Cog):

    def __init__(self, bot):
        self.client = bot
        self.queue = []

    @commands.command()
    async def play(self, ctx, *, search):
        try:
            await join_voice_channel(ctx)
            await add_to_queue(ctx, search, self.queue)
            if not ctx.voice_client.is_playing():
                await play_next(ctx, self.queue, self.client)
        except Exception as e:
            await ctx.send(f"An error occurred: {str(e)}")

    @commands.command()
    async def skip(self, ctx):
        try:
            if ctx.voice_client and ctx.voice_client.is_playing():
                ctx.voice_client.stop()
                await ctx.send("Skipped the current song.")
        except Exception as e:
            await ctx.send(
                f"An error occurred while skipping the song: {str(e)}")

    @commands.command()
    async def ping(self, ctx):
        await ctx.send('pong')

    @commands.command()
    async def djhelp(self, ctx):
        await ctx.send('Available commands:\n'
                       '/clear - Clear the current queue\n'
                       '/ping - Ping the bot\n'
                       '/play <search> - Play a song from YouTube\n'
                       '/showq - Show the current queue\n'
                       '/skip - Skip the current song\n'
                       '/toggle - Toggle pause|continue playback\n')

    @commands.command()
    async def clear(self, ctx):
        try:
            self.queue.clear()
            await ctx.send("Queue cleared.")
        except Exception as e:
            await ctx.send(
                f"An error occurred while clearing the queue: {str(e)}")

    @commands.command()
    async def showq(self, ctx):
        queue_list = ''
        if not self.queue:
            await ctx.send("The queue is empty.")
            return
        for i, song in enumerate(self.queue):
            queue_list += f"{i+1}. {song[1]}\n"
            await ctx.send(f"Queue:\n{queue_list}")

    @commands.command()
    async def toggle(self, ctx):
        if ctx.voice_client.is_playing():
            await ctx.voice_client.pause()
        else:
            await ctx.voice_client.resume()
