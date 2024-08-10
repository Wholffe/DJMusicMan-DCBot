import discord
import yt_dlp

from .config import FFMPEG_OPTIONS, YDL_OPTIONS


async def get_info(search):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
        return info
    except Exception as e:
        print(f"Error fetching video information: {str(e)}")
        return None


async def play_next(ctx, queue, client) -> None:
    try:
        if queue:
            url, title = queue.pop(0)
            source = await discord.FFmpegOpusAudio.from_probe(
                url, **FFMPEG_OPTIONS)
            ctx.voice_client.play(source,
                                  after=lambda _: client.loop.create_task(
                                      play_next(ctx, queue, client)))
            await ctx.send(f"Now playing: {title}")
        elif not ctx.voice_client.is_playing():
            await ctx.send("Queue is empty. Use /play to add songs.")
    except Exception as e:
        await ctx.send(f"An error occurred while playing the song: {str(e)}")


async def join_voice_channel(ctx) -> None:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        return await ctx.send("You are not connected to a voice channel.")
    if not ctx.voice_client:
        await voice_channel.connect()


async def add_to_queue(ctx, search, queue) -> None:
    async with ctx.typing():
        info = await get_info(search)
        if not info:
            return await ctx.send("Failed to retrieve the video information.")
        if isinstance(info, dict) and 'entries' in info:
            info = info['entries'][0]
        if not ('url' in info or 'title' in info):
            return await ctx.send("Failed to retrieve the video URL or title.")
        url, title = info['url'], info['title']
        queue.append((url, title))
        await ctx.send(f"Added to queue: {title}")
