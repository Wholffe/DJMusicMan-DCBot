import discord
import yt_dlp
import asyncio

from .config import FFMPEG_OPTIONS, YDLP_OPTIONS
from music_bot import constants as CONST

idle_timer = 0
max_duration_timeout = 180
timer_task = None

def error_handling(func):
    """Decorator to handle exceptions in commands."""
    async def wrapper(ctx, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except Exception as e:
            await ctx.send(f"An error occurred while executing the command: {e}")
    return wrapper

# ------------------------- Commands -------------------------

@error_handling
async def cm_clear(musicbot, ctx) -> None:
    musicbot.queue.clear()
    await send_message(ctx, CONST.MESSAGE_QUEUE_CLEARED)

@error_handling
async def cm_djhelp(ctx) -> None:
    await send_message(ctx, CONST.MESSAGE_HELP)

@error_handling
async def cm_leave(ctx) -> None:
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@error_handling
async def cm_ping(ctx) -> None:
    await send_message(ctx, CONST.MESSAGE_PONG)

@error_handling
async def cm_play(musicbot, ctx, search) -> bool:
    if (not await join_voice_channel(ctx) or not await queue_add(ctx, search, musicbot.queue)):
        return
    if not await is_playing(ctx):
        await play_next(ctx, musicbot.queue, musicbot.client)

@error_handling
async def cm_showq(musicbot, ctx) -> None:
    if not musicbot.queue:
        await send_message(ctx, CONST.MESSAGE_QUEUE_EMPTY)
        return
    queue_list = "\n".join([f"{i+1}. {song[1]}" for i, song in enumerate(musicbot.queue)])
    await send_message(ctx, f'Queue:\n{queue_list}')

@error_handling
async def cm_skip(ctx) -> None:
    if await is_playing(ctx):
        ctx.voice_client.stop()
        await send_message(ctx, CONST.MESSAGE_SKIPPED_SONG)

@error_handling
async def cm_toggle(ctx) -> None:
    if await is_playing(ctx):
        await ctx.voice_client.pause()
    else:
        await ctx.voice_client.resume()

# ------------------------- Helper -------------------------

async def get_info(search) -> dict:
    with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
        info = ydl.extract_info(search, download=False)
    if 'entries' in info:
        info = info['entries'][0]
    return info

async def is_playing(ctx) -> bool:
    return ctx.voice_client and ctx.voice_client.is_playing()

async def join_voice_channel(ctx) -> bool:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await send_message(ctx, CONST.MESSAGE_NOT_CONNECTED)
        return False
    if not ctx.voice_client:
        await voice_channel.connect()
    return True

async def play_next(ctx, queue, client) -> None:
    global idle_timer, timer_task

    if not queue:
        if ctx.voice_client and not ctx.voice_client.is_playing() and not timer_task:
            timer_task = asyncio.create_task(start_idle_timer(ctx))
        await send_message(ctx, CONST.MESSAGE_QUEUE_EMPTY_USE_PLAY)
        return

    url, title = queue.pop(0)
    idle_timer = 0
    if timer_task:
        timer_task.cancel()
        timer_task = None

    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(
        source,
        after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
    )
    await send_message(ctx, f'Now playing: {title}')

async def queue_add(ctx, search, queue) -> bool:
    async with ctx.typing():
        info = await get_info(search)
        if not info or 'url' not in info or 'title' not in info:
            await send_message(ctx, CONST.MESSAGE_FAILED_VIDEO_INFO)
            return False
        url, title = info['url'], info['title']
        queue.append((url, title))
        await send_message(ctx, f'Added to queue: {title}')
        return True

async def send_message(ctx, text: str) -> None:
    await ctx.send(text)

async def start_idle_timer(ctx) -> None:
    global idle_timer, max_duration_timeout
    idle_timer = 0

    while ctx.voice_client and idle_timer < max_duration_timeout:
        await asyncio.sleep(1)
        if ctx.voice_client.is_playing():
            return
        idle_timer += 1

    await cm_leave(ctx)
    await send_message(ctx, CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)