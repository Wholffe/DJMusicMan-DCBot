import discord
import yt_dlp
import asyncio

from .config import FFMPEG_OPTIONS, YDLP_OPTIONS
from music_bot import constants as CONST


idle_timer = 0
max_duration_timeout = 10
timer_task = None

async def get_info(ctx, search):
    try:
        with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
        if 'entries' in info:
            info = info['entries'][0]
        return info
    except Exception as e:
        handle_error(ctx, CONST.ACTION_FETCHING_VIDEO_INFOS, e)

async def start_idle_timer(ctx):
    global idle_timer, max_duration_timeout
    idle_timer = 0

    while ctx.voice_client and idle_timer < max_duration_timeout:
        await asyncio.sleep(1)
        if ctx.voice_client.is_playing():
            return
        idle_timer += 1

    if ctx.voice_client:    
        await ctx.send(CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)
        await ctx.voice_client.disconnect()

async def play_next(ctx, queue, client) -> None:
    global idle_timer, timer_task

    if not queue:
        if ctx.voice_client and not ctx.voice_client.is_playing() and not timer_task:
            timer_task = asyncio.create_task(start_idle_timer(ctx))
        await ctx.send(CONST.MESSAGE_QUEUE_EMPTY_USE_PLAY)
        return

    url, title = queue.pop(0)
    idle_timer = 0
    if timer_task:
        timer_task.cancel()
        timer_task = None

    try:
        source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
        ctx.voice_client.play(
            source,
            after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
        )
        await ctx.send(f"Now playing: {title}")
    except Exception as e:
        await handle_error(ctx, CONST.ACTION_PLAYING_SONG, e)


async def join_voice_channel(ctx) -> bool:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await ctx.send(CONST.MESSAGE_NOT_CONNECTED)
        return
    if not ctx.voice_client:
        await voice_channel.connect()
    return True


async def add_to_queue(ctx, search, queue) -> bool:
    async with ctx.typing():
        info = await get_info(ctx, search)
        if not (info or 'url' in info or 'title' in info):
            await ctx.send(CONST.MESSAGE_FAILED_VIDEO_INFO)
            return
        url, title = info['url'], info['title']
        queue.append((url, title))
        await ctx.send(f"Added to queue: {title}")
        return True


async def handle_error(ctx, action: str, error: Exception) -> None:
    await ctx.send(f"An error occurred while {action}: {str(error)}")


async def is_playing(ctx) -> bool:
    return ctx.voice_client and ctx.voice_client.is_playing()