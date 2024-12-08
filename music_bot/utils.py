import discord
import yt_dlp
import asyncio

from .config import YDLP_OPTIONS,FFMPEG_OPTIONS
from music_bot import constants as CONST
from .message_handler import MessageHandler
from .music_queue import MusicQueue

message_handler = MessageHandler()

def error_handling(func):
    """Decorator to handle exceptions in commands."""
    async def wrapper(ctx, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except Exception as e:
            await ctx.send(f"An error occurred while executing the command: {e}")
    return wrapper

async def get_info(search: str) -> dict:
    with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
        info = ydl.extract_info(search, download=False)
    if 'entries' in info:
        info = info['entries'][0]
    return {'url': info.get('url'), 'title': info.get('title')}

async def join_voice_channel(ctx) -> bool:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await message_handler.send_error(ctx, CONST.MESSAGE_NOT_CONNECTED)
        return False
    if not ctx.voice_client:
        await voice_channel.connect()
    return True

async def is_playing(ctx) -> bool:
    return ctx.voice_client and ctx.voice_client.is_playing()

async def play_next(ctx, queue: MusicQueue, client):
    if queue.is_empty():
        await handle_idle(ctx)
        return

    song = queue.get_next_song()
    if not song:
        await handle_idle(ctx)
        return

    url, title = song
    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(
        source,
        after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
    )
    await message_handler.send_success(ctx, f'Now playing: {title}')

async def handle_idle(ctx):
    """Handles the bot's behavior when the queue is empty."""
    global timer_task
    if not timer_task:
        timer_task = asyncio.create_task(start_idle_timer(ctx))
    await message_handler.send_info(ctx, CONST.MESSAGE_QUEUE_EMPTY_USE_PLAY)

async def start_idle_timer(ctx):
    """Starts an idle timer to disconnect the bot after inactivity."""
    global idle_timer, max_duration_timeout
    idle_timer = 0

    while ctx.voice_client and idle_timer < max_duration_timeout:
        await asyncio.sleep(1)
        if ctx.voice_client.is_playing():
            return
        idle_timer += 1

    await ctx.voice_client.disconnect()
    await message_handler.send_info(ctx, CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)

@error_handling
async def cm_play(musicbot, ctx, search):
    if not await join_voice_channel(ctx):
        return

    info = await get_info(search)
    if 'error' in info:
        await message_handler.send_error(ctx, f"Error: {info['error']}")
        return

    musicbot.queue.add_song(info['url'], info['title'])
    await message_handler.send_success(ctx, f"Added to queue: {info['title']}")

    if not await is_playing(ctx):
        await play_next(ctx, musicbot.queue, musicbot.client)

@error_handling
async def cm_skip(ctx):
    if await is_playing(ctx):
        ctx.voice_client.stop()
        await message_handler.send_success(ctx, CONST.MESSAGE_SKIPPED_SONG)

@error_handling
async def cm_showq(musicbot, ctx):
    if musicbot.queue.is_empty():
        await message_handler.send_info(ctx, CONST.MESSAGE_QUEUE_EMPTY)
        return

    queue_list = musicbot.queue.list_queue()
    await message_handler.send_info(ctx, f'Queue:\n{queue_list}')

@error_handling
async def cm_clear(musicbot, ctx):
    musicbot.queue.clear()
    await message_handler.send_success(ctx, CONST.MESSAGE_QUEUE_CLEARED)

@error_handling
async def cm_leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@error_handling
async def cm_toggle(ctx):
    if await is_playing(ctx):
        ctx.voice_client.pause()
    else:
        ctx.voice_client.resume()

@error_handling
async def cm_djhelp(ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_HELP)

@error_handling
async def cm_ping(ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_PONG)