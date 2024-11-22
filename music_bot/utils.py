import discord
import yt_dlp
import asyncio

from .config import FFMPEG_OPTIONS, YDLP_OPTIONS
from music_bot import constants as CONST

# Global variables
idle_timer = 0
max_duration_timeout = 180
timer_task = None


# ------------------------- Commands -------------------------

async def cm_clear(musicbot, ctx) -> None:
    """
    Clears the music queue.
    """
    musicbot.queue.clear()
    await send_message(ctx, CONST.MESSAGE_QUEUE_CLEARED)


async def cm_djhelp(ctx) -> None:
    """
    Sends the help message.
    """
    await send_message(ctx, CONST.MESSAGE_HELP)


async def cm_leave(ctx) -> None:
    """
    Disconnects the bot from the voice channel.
    """
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


async def cm_ping(ctx) -> None:
    """
    Sends a pong response to check if the bot is responsive.
    """
    await send_message(ctx, CONST.MESSAGE_PONG)


async def cm_play(musicbot, ctx, search) -> bool:
    """
    Plays a song or adds it to the queue.
    Returns:
        bool: True if the operation succeeded, otherwise False.
    """
    if not await join_voice_channel(ctx):
        return False
    if not await queue_add(ctx, search, musicbot.queue):
        return False
    if not await is_playing(ctx):
        await play_next(ctx, musicbot.queue, musicbot.client)


async def cm_showq(musicbot, ctx) -> None:
    """
    Displays the current music queue.
    """
    if not musicbot.queue:
        await send_message(ctx, CONST.MESSAGE_QUEUE_EMPTY)
        return
    queue_list = "\n".join([f"{i+1}. {song[1]}" for i, song in enumerate(musicbot.queue)])
    await send_message(ctx, f'Queue:\n{queue_list}')


async def cm_skip(ctx) -> None:
    """
    Skips the currently playing song.
    """
    if await is_playing(ctx):
        ctx.voice_client.stop()
        await send_message(ctx, CONST.MESSAGE_SKIPPED_SONG)


async def cm_toggle(ctx) -> None:
    """
    Toggles playback between pause and resume.
    """
    if await is_playing(ctx):
        await ctx.voice_client.pause()
    else:
        await ctx.voice_client.resume()


# ------------------------- Helper -------------------------

def error_handling(func):
    """Decorator to handle exceptions in commands."""
    async def wrapper(self, ctx, *args, **kwargs):
        try:
            await func(self, ctx, *args, **kwargs)
        except Exception as e:
            await ctx.send(f"An error occurred while executing the command: {e}")
    return wrapper


async def get_info(search) -> dict:
    """
    Retrieves video information using yt_dlp.
    Returns:
        dict: The video information, or None if an error occurs.
    """
    with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
        info = ydl.extract_info(search, download=False)
    if 'entries' in info:
        info = info['entries'][0]
    return info


async def is_playing(ctx) -> bool:
    """
    Checks if the bot is currently playing audio.
    Returns:
        bool: True if playing, False otherwise.
    """
    return ctx.voice_client and ctx.voice_client.is_playing()


async def join_voice_channel(ctx) -> bool:
    """
    Joins the user's voice channel if possible.
    Returns:
        bool: True if successfully joined, False otherwise.
    """
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await send_message(ctx, CONST.MESSAGE_NOT_CONNECTED)
        return False
    if not ctx.voice_client:
        await voice_channel.connect()
    return True


async def play_next(ctx, queue, client) -> None:
    """
    Plays the next song in the queue.
    """
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
    """
    Adds a song to the queue.
    Returns:
        bool: True if the song was added successfully, False otherwise.
    """
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
    """
    Sends a message to the user.
    """
    await ctx.send(text)


async def start_idle_timer(ctx) -> None:
    """
    Starts an inactivity timer and leaves the voice channel after a timeout.
    """
    global idle_timer, max_duration_timeout
    idle_timer = 0

    while ctx.voice_client and idle_timer < max_duration_timeout:
        await asyncio.sleep(1)
        if ctx.voice_client.is_playing():
            return
        idle_timer += 1

    await cm_leave(ctx)
    await send_message(ctx, CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)