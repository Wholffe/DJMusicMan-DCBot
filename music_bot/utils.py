import discord
import yt_dlp

from .config import YDLP_OPTIONS,FFMPEG_OPTIONS
from music_bot import constants as CONST
from .message_handler import MessageHandler
from .music_queue import MusicQueue
from .idle_timer import IdleTimer
import asyncio
from concurrent.futures import ThreadPoolExecutor


message_handler = MessageHandler()
idle_timer = IdleTimer()
executor = ThreadPoolExecutor(max_workers=5)

def error_handling(func):
    """Decorator to handle exceptions in commands."""
    async def wrapper(ctx, *args, **kwargs):
        try:
            await func(ctx, *args, **kwargs)
        except Exception as e:
            await message_handler.send_error(ctx,f'An error occurred while executing the command: {e}')
    return wrapper

def extract_song_infos(search: str) -> list:
    try:
        with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
            info = ydl.extract_info(search, download=False)
    except yt_dlp.utils.DownloadError:
        return []
    
    entries = info.get('entries') if 'entries' in info and isinstance(info['entries'], list) else [info]

    songs = [
        {
            'url': entry.get('url'),
            'title': entry.get('title'),
        }
        for entry in entries if entry
    ]
    return songs

async def get_song_infos(search: str) -> list:
    loop = asyncio.get_event_loop()
    songs = await loop.run_in_executor(executor, extract_song_infos, search)
    return songs

async def join_voice_channel(musicbot,ctx) -> bool:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await message_handler.send_error(ctx, CONST.MESSAGE_NOT_CONNECTED)
        return False
    if not ctx.voice_client:
        await voice_channel.connect()
        musicbot.queue.set_loop(False)
    return True

async def is_playing(ctx) -> bool:
    return ctx.voice_client and ctx.voice_client.is_playing()

@error_handling
async def play_next(ctx, queue: MusicQueue, client):
    song = queue.get_next_song()
    if queue.is_empty() and (not song):
        await idle_timer.handle_idle(ctx)
        return

    idle_timer.clear_timer_task()
    url, title = song
    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(
        source,
        after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
    )
    current_song_info = queue.get_current_song_info()
    await message_handler.send_success(ctx, current_song_info)

@error_handling
async def cm_play(musicbot, ctx, search):
    if not await join_voice_channel(musicbot,ctx):
        return

    async with ctx.typing():
        songs = await get_song_infos(search)
        if not songs:
            await message_handler.send_error(ctx, CONST.MESSAGE_FAILED_VIDEO_INFO)
            return

        for song in songs:
            musicbot.queue.add_song(song['url'], song['title'])

        if len(songs) > 1:
            await message_handler.send_success(ctx, f"Added {len(songs)} songs to the queue.")
        else:
            await message_handler.send_success(ctx, f"Added to queue: {songs[0]['title']}")

    if not await is_playing(ctx):
        await play_next(ctx, musicbot.queue, musicbot.client)

@error_handling
async def cm_skip(musicbot,ctx):
    musicbot.queue.set_loop(False)
    if await is_playing(ctx):
        ctx.voice_client.stop()
        await message_handler.send_success(ctx, CONST.MESSAGE_SKIPPED_SONG)

@error_handling
async def cm_showq(musicbot, ctx):
    if not musicbot.queue.current_song:
        await message_handler.send_info(ctx, CONST.MESSAGE_QUEUE_EMPTY)
        return

    current_song_info = f'Current song: {musicbot.queue.get_current_song_info()}'
    loop_status = "Enabled" if musicbot.queue.loop else "Disabled"
    queue_songs, remaining_songs = musicbot.queue.list_queue_with_limit()

    queue_embed = CONST.get_queue_embed()
    if current_song_info:
        queue_embed["fields"].append({"name": "Now Playing", "value": current_song_info, "inline": True})
        queue_embed["fields"].append({"name": "Loop Status", "value": loop_status, "inline": True})

    if queue_songs:
        queue_embed["fields"].append({"name": "Up Next", "value": queue_songs, "inline": False})
        if remaining_songs > 0:
            queue_embed["fields"].append({"name": "And more...", "value": f"{remaining_songs} more items", "inline": False})
    else:
        queue_embed["fields"].append({"name": "Queue", "value": "The queue is empty.", "inline": False})
    await message_handler.send_embed(ctx, queue_embed)

@error_handling
async def cm_clear(musicbot, ctx):
    musicbot.queue.clear()
    await message_handler.send_success(ctx, CONST.MESSAGE_QUEUE_CLEARED)

@error_handling
async def cm_leave(ctx):
    idle_timer.clear_timer_task()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@error_handling
async def cm_toggle(ctx):
    if await is_playing(ctx):
        ctx.voice_client.pause()
        await message_handler.send_success(ctx, CONST.MESSAGE_PAUSED_SONG)
    else:
        ctx.voice_client.resume()
        await message_handler.send_success(ctx, CONST.MESSAGE_RESUMED_SONG)

@error_handling
async def cm_djhelp(ctx) -> None:
    embed_dict = CONST.get_djhelp_embed()
    await message_handler.send_embed(ctx, embed_dict)

@error_handling
async def cm_ping(ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_PONG)

@error_handling
async def cm_shuffle(musicbot,ctx) -> None:
    musicbot.queue.shuffle_queue()
    await message_handler.send_success(ctx, CONST.MESSAGE_QUEUE_SHUFFLED)

@error_handling
async def cm_loop(musicbot,ctx) -> None:
    musicbot.queue.toggle_loop()
    await message_handler.send_success(ctx, f"Looping is {'enabled' if musicbot.queue.loop else 'disabled'}.")

@error_handling
async def cm_remove(musicbot,ctx,index) -> None:
    removed_song = musicbot.queue.remove_song(index-1) # 1-based index
    if removed_song:
        await message_handler.send_success(ctx,f"Removed from queue: {removed_song[1]}")
    else:
        await message_handler.send_error(ctx,f"Invalid queue number: {index}")