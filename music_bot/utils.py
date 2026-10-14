import asyncio
import functools
from concurrent.futures import ThreadPoolExecutor

import discord

from music_bot import constants as CONST

from .cache_manager import CacheManager, ProgressHook
from .command_handler import CommandHandler
from .config import FFMPEG_OPTIONS
from .idle_timer import IdleTimer
from .logger import log_command
from .message_handler import MessageHandler
from .music_queue import MusicQueue
from .progressbar import DownloadProgress

# region Global Instances
message_handler = MessageHandler()
idle_timer = IdleTimer()
cache_manager = CacheManager()
command_handler = CommandHandler(message_handler)
executor = ThreadPoolExecutor(max_workers=5)


# region Asynchronous Helpers
async def get_song_infos(
    searches: str | list[str], progress_hook: ProgressHook | None = None
) -> list[dict[str, str]]:
    """Asynchronously fetches song information using the CacheManager."""
    if isinstance(searches, str):
        searches = [searches]

    loop = asyncio.get_running_loop()
    get_songs = functools.partial(cache_manager.get_songs, progress_hook=progress_hook)
    tasks = [loop.run_in_executor(executor, get_songs, search) for search in searches]
    results = await asyncio.gather(*tasks)
    return [song for result in results for song in result]


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


async def is_playing(ctx) -> bool:
    return bool(ctx.voice_client and ctx.voice_client.is_playing())


async def play_song(ctx, queue: MusicQueue, client, url: str, title: str) -> None:
    source = await discord.FFmpegOpusAudio.from_probe(url, **FFMPEG_OPTIONS)
    ctx.voice_client.play(
        source, after=lambda _: client.loop.create_task(play_next(ctx, queue, client))
    )


async def is_bot_only_member_in_vc(ctx) -> bool:
    return bool(ctx.voice_client and len(ctx.voice_client.channel.members) == 1)


@command_handler.handle_errors
async def play_next(ctx, queue: MusicQueue, client) -> None:
    song = queue.get_next_song()
    if not song:
        await idle_timer.handle_idle(ctx)
        return

    if await is_bot_only_member_in_vc(ctx):
        await cm_leave(ctx)
        await message_handler.send_info(ctx, CONST.MESSAGE_NO_USERS_IN_CHANNEL)
        return

    idle_timer.clear_timer_task()
    if not ctx.voice_client:
        return

    url, title = song
    await play_song(ctx, queue, client, url, title)


async def _add_songs_to_queue(
    ctx, queue: MusicQueue, search: str, add_to_front: bool = False
) -> bool:
    async with ctx.typing():
        if search.lower().startswith("www.youtube.com"):
            search = f"https://{search}"

        progress = DownloadProgress(ctx, asyncio.get_running_loop(), message_handler)
        songs = await get_song_infos(search, progress)
        if not songs:
            await message_handler.send_error(ctx, CONST.MESSAGE_FAILED_VIDEO_INFO)
            return False

        add_song = queue.add_song_first if add_to_front else queue.add_song
        for song in reversed(songs) if add_to_front else songs:
            add_song(song["url"], song["title"])

        queue_position = "front of the queue" if add_to_front else "queue"
        if len(songs) > 1:
            message = f"Added {len(songs)} songs to the {queue_position}."
        else:
            message = f"Added to the {queue_position}: {songs[0]['title']}"

        await message_handler.send_success(ctx, message)
        return True


def get_latency_color(ms: int) -> discord.Color:
    MAX_MS = 500
    ms = max(0, min(ms, MAX_MS))
    ratio = ms / MAX_MS

    GREEN = (67, 181, 129)
    RED = (240, 71, 71)

    r = int(GREEN[0] + (RED[0] - GREEN[0]) * ratio)
    g = int(GREEN[1] + (RED[1] - GREEN[1]) * ratio)
    b = int(GREEN[2] + (RED[2] - GREEN[2]) * ratio)

    return discord.Color.from_rgb(r, g, b)


async def _queue_and_play(musicbot, ctx, search: str, add_to_front: bool) -> None:
    """Joins the voice channel, queues the search results and starts playback."""
    if not await join_voice_channel(musicbot, ctx):
        return
    if not await _add_songs_to_queue(ctx, musicbot.queue, search, add_to_front):
        return
    if not await is_playing(ctx):
        await play_next(ctx, musicbot.queue, musicbot.client)


# region CM_Commands
@command_handler.handle_errors
@log_command
async def cm_play(musicbot, ctx, search: str) -> None:
    await _queue_and_play(musicbot, ctx, search, add_to_front=False)


@command_handler.handle_errors
@log_command
async def cm_playfirst(musicbot, ctx, search: str) -> None:
    await _queue_and_play(musicbot, ctx, search, add_to_front=True)


@command_handler.handle_errors
async def cm_skip(musicbot, ctx) -> None:
    if not await is_playing(ctx):
        return
    musicbot.queue.skip_current_song(ctx)
    await message_handler.send_success(ctx, CONST.MESSAGE_SKIPPED_SONG)


@command_handler.handle_errors
async def cm_showq(musicbot, ctx) -> None:
    if not musicbot.queue.current_song:
        await message_handler.send_info(ctx, CONST.MESSAGE_QUEUE_EMPTY)
        return

    current_song_info = f"Current song: {musicbot.queue.get_current_song_info()}"
    loop_status = "Enabled" if musicbot.queue.loop else "Disabled"
    queue_songs, remaining_songs = musicbot.queue.list_queue_with_limit()

    queue_embed = CONST.get_queue_embed()
    queue_embed["fields"].append(
        {"name": "Now Playing", "value": current_song_info, "inline": True}
    )
    queue_embed["fields"].append(
        {"name": "Loop Status", "value": loop_status, "inline": True}
    )

    if queue_songs:
        queue_embed["fields"].append(
            {"name": "Up Next", "value": queue_songs, "inline": False}
        )
    if remaining_songs > 0:
        queue_embed["fields"].append(
            {
                "name": "And more...",
                "value": f"{remaining_songs} more items",
                "inline": False,
            }
        )
    if not queue_songs and not remaining_songs:
        queue_embed["fields"].append(
            {"name": "Queue", "value": CONST.MESSAGE_QUEUE_EMPTY, "inline": False}
        )
    await message_handler.send_custom(ctx, queue_embed)


@command_handler.handle_errors
async def cm_clear(musicbot, ctx) -> None:
    musicbot.queue.clear()
    await message_handler.send_success(ctx, CONST.MESSAGE_QUEUE_CLEARED)


@command_handler.handle_errors
async def cm_leave(ctx) -> None:
    idle_timer.clear_timer_task()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()


@command_handler.handle_errors
async def cm_toggle(ctx) -> None:
    if await is_playing(ctx):
        ctx.voice_client.pause()
        await message_handler.send_success(ctx, CONST.MESSAGE_PAUSED_SONG)
    else:
        ctx.voice_client.resume()
        await message_handler.send_success(ctx, CONST.MESSAGE_RESUMED_SONG)


@command_handler.handle_errors
async def cm_djhelp(ctx) -> None:
    embed_dict = CONST.get_djhelp_embed()
    await message_handler.send_custom(ctx, embed_dict)


@command_handler.handle_errors
async def cm_ping(ctx) -> None:
    latency_ms = round(ctx.bot.latency * 1000)

    color = get_latency_color(latency_ms)
    await message_handler.send_colored(ctx, f"ping: {latency_ms}ms", color)


@command_handler.handle_errors
async def cm_shuffle(musicbot, ctx) -> None:
    musicbot.queue.shuffle_queue()
    await message_handler.send_success(ctx, CONST.MESSAGE_QUEUE_SHUFFLED)


@command_handler.handle_errors
async def cm_loop(musicbot, ctx) -> None:
    musicbot.queue.toggle_loop()
    await message_handler.send_success(
        ctx, f"Looping is {'enabled' if musicbot.queue.loop else 'disabled'}."
    )


@command_handler.handle_errors
async def cm_remove(musicbot, ctx, index: int) -> None:
    removed_song = musicbot.queue.remove_song(index - 1)  # 1-based index
    if removed_song:
        await message_handler.send_success(
            ctx, f"Removed from queue: {removed_song[1]}"
        )
    else:
        await message_handler.send_error(ctx, f"Invalid queue number: {index}")


@log_command
async def cm_restart(musicbot, ctx) -> None:
    await message_handler.send_info(ctx, CONST.MESSAGE_RESTARTING_BOT)
    musicbot.queue.set_loop(False)
    await cm_leave(ctx)
    await musicbot.client.close()


@command_handler.handle_errors
async def cm_clear_cache(ctx) -> None:
    if ctx.voice_client:
        await message_handler.send_error(
            ctx, CONST.MESSAGE_CANNOT_CLEAR_CACHE_WHILE_CONNECTED
        )
        return
    deleted_files, total_size_mb = cache_manager.clear_cache()
    await message_handler.send_success(
        ctx,
        f"Cleared cache: Deleted {deleted_files} files, freeing {total_size_mb} MB.",
    )
