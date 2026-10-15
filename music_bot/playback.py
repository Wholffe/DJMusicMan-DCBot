import asyncio
import contextlib
from collections.abc import AsyncIterator
from concurrent.futures import Future

import discord

from music_bot import constants as CONST

from .cache_manager import ProgressHook
from .config import FFMPEG_OPTIONS
from .logger import logger
from .music_queue import MusicQueue, Song
from .progressbar import DownloadProgress
from .services import (
    cache_manager,
    command_handler,
    executor,
    idle_timer,
    message_handler,
)


# region Song Loading
async def iter_song_infos(
    search: str, progress_hook: ProgressHook | None = None
) -> AsyncIterator[dict[str, str]]:
    """Asynchronously yields song information as soon as each song is ready."""
    loop = asyncio.get_running_loop()
    songs = cache_manager.iter_songs(search, progress_hook)
    try:
        while True:
            # StopIteration cannot be raised into a Future, so next gets a default
            song = await loop.run_in_executor(executor, next, songs, None)
            if song is None:
                return
            yield song
    finally:
        # A cancelled task leaves next running in its thread, closing would fail
        if not songs.gi_running:
            await loop.run_in_executor(executor, songs.close)


async def _add_songs_to_queue(
    ctx, queue: MusicQueue, client, search: str, add_to_front: bool = False
) -> bool:
    if search.lower().startswith("www.youtube.com"):
        search = f"https://{search}"

    progress = DownloadProgress(ctx, asyncio.get_running_loop(), message_handler)
    generation = queue.generation
    anchor: Song | None = None
    titles: list[str] = []
    queue.loading += 1
    try:
        async with contextlib.aclosing(iter_song_infos(search, progress)) as songs:
            async for song in songs:
                # The queue was cleared or the bot left the voice channel
                if queue.generation != generation or not ctx.voice_client:
                    break
                if add_to_front:
                    anchor = queue.add_song_after(anchor, song["url"], song["title"])
                else:
                    queue.add_song(song["url"], song["title"])
                titles.append(song["title"])
                await start_playback_if_idle(ctx, queue, client)
    except Exception:
        # Don't leave the progress message behind, handle_errors reports the error
        await progress.finish(CONST.MESSAGE_FAILED_VIDEO_INFO, success=False)
        raise
    finally:
        queue.loading -= 1
        # play_next skips the idle handling while songs are loading, so catch up
        if ctx.voice_client and not queue.current_song:
            await start_playback_if_idle(ctx, queue, client)

    stopped = queue.generation != generation or not ctx.voice_client
    success = bool(titles) and not stopped
    queue_position = "front of the queue" if add_to_front else "queue"
    if stopped:
        message = CONST.MESSAGE_ADDING_SONGS_STOPPED
    elif not titles:
        message = CONST.MESSAGE_FAILED_VIDEO_INFO
    elif len(titles) > 1:
        message = f"Added {len(titles)} songs to the {queue_position}."
    else:
        message = f"Added to the {queue_position}: {titles[0]}"

    if not await progress.finish(message, success=success):
        send = message_handler.send_success if success else message_handler.send_error
        await send(ctx, message)
    return success


async def queue_and_play(musicbot, ctx, search: str, add_to_front: bool) -> None:
    """Joins the voice channel, queues the search results and starts playback."""
    await ctx.defer()
    if not await join_voice_channel(musicbot, ctx):
        return
    await _add_songs_to_queue(
        ctx, musicbot.queue, musicbot.client, search, add_to_front
    )


# region Voice
async def join_voice_channel(musicbot, ctx) -> bool:
    voice_channel = ctx.author.voice.channel if ctx.author.voice else None
    if not voice_channel:
        await message_handler.send_error(ctx, CONST.MESSAGE_NOT_CONNECTED)
        return False
    if not ctx.voice_client:
        await voice_channel.connect()
        for _ in range(10):
            await asyncio.sleep(0.1)
            if ctx.voice_client:
                break
        musicbot.queue.clear()
        musicbot.queue.set_loop(False)
    return True


async def leave_voice_channel(ctx) -> None:
    idle_timer.clear_timer_task()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


async def is_playing(ctx) -> bool:
    return bool(ctx.voice_client and ctx.voice_client.is_playing())


async def is_bot_only_member_in_vc(ctx) -> bool:
    return bool(ctx.voice_client and len(ctx.voice_client.channel.members) == 1)


def _log_playback_error(future: Future[None]) -> None:
    """Logs the error if starting the next song failed."""
    error = None if future.cancelled() else future.exception()
    if error:
        logger.error("Failed to start the next song", exc_info=error)


async def play_song(ctx, queue: MusicQueue, client, url: str, title: str) -> None:
    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)

    # discord.py calls after from its player thread, not from the event loop
    def after(_) -> None:
        future = asyncio.run_coroutine_threadsafe(
            start_playback_if_idle(ctx, queue, client), client.loop
        )
        future.add_done_callback(_log_playback_error)

    ctx.voice_client.play(source, after=after)


async def start_playback_if_idle(ctx, queue: MusicQueue, client) -> None:
    """Plays the next song unless audio is already playing."""
    async with queue.playback_lock:
        voice_client = ctx.voice_client
        # A paused song must not be replaced by a newly loaded one
        if voice_client and (voice_client.is_playing() or voice_client.is_paused()):
            return
        await play_next(ctx, queue, client)


@command_handler.handle_errors
async def play_next(ctx, queue: MusicQueue, client) -> None:
    song = queue.get_next_song()
    if not song:
        # A loading playlist restarts playback with its next song
        if queue.loading:
            return
        await idle_timer.handle_idle(ctx)
        return

    if await is_bot_only_member_in_vc(ctx):
        await leave_voice_channel(ctx)
        await message_handler.send_info(ctx, CONST.MESSAGE_NO_USERS_IN_CHANNEL)
        return

    idle_timer.clear_timer_task()
    if not ctx.voice_client:
        return

    url, title = song
    await play_song(ctx, queue, client, url, title)
