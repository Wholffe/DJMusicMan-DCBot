import discord
import yt_dlp

from .config import YDLP_OPTIONS,FFMPEG_OPTIONS
from music_bot import constants as CONST
from .message_handler import MessageHandler
from .music_queue import MusicQueue
from .idle_timer import IdleTimer


message_handler = MessageHandler()
idle_timer = IdleTimer()

def error_handling(func):
    """Decorator to handle exceptions in commands."""
    async def wrapper(ctx, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except Exception as e:
            await message_handler.send_error(ctx,f'An error occurred while executing the command: {e}')
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
        await idle_timer.handle_idle(ctx)
        return

    song = queue.get_next_song()
    if not song:
        await idle_timer.handle_idle(ctx)
        return

    url, title = song
    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(
        source,
        after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
    )
    await message_handler.send_success(ctx, f'Now playing: {title}')

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
        await ctx.voice_client.pause()
    else:
        await ctx.voice_client.resume()

@error_handling
async def cm_djhelp(ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_HELP)

@error_handling
async def cm_ping(ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_PONG)