import discord

from music_bot import constants as CONST

from .logger import log_command
from .playback import is_playing, leave_voice_channel, queue_and_play
from .services import cache_manager, command_handler, message_handler


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


# region CM_Commands
@command_handler.handle_errors
@log_command
async def cm_play(musicbot, ctx, search: str) -> None:
    await queue_and_play(musicbot, ctx, search, add_to_front=False)


@command_handler.handle_errors
@log_command
async def cm_playfirst(musicbot, ctx, search: str) -> None:
    await queue_and_play(musicbot, ctx, search, add_to_front=True)


@command_handler.handle_errors
async def cm_skip(musicbot, ctx) -> None:
    voice_client = ctx.voice_client
    if not voice_client or not (voice_client.is_playing() or voice_client.is_paused()):
        await message_handler.send_info(ctx, CONST.MESSAGE_NOTHING_PLAYING)
        return
    musicbot.queue.skip_current_song(ctx)
    await message_handler.send_success(ctx, CONST.MESSAGE_SKIPPED_SONG)


@command_handler.handle_errors
async def cm_queue(musicbot, ctx) -> None:
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
    await ctx.defer()
    if not ctx.voice_client:
        await message_handler.send_info(ctx, CONST.MESSAGE_BOT_NOT_IN_VOICE)
        return
    await leave_voice_channel(ctx)
    await message_handler.send_success(ctx, CONST.MESSAGE_LEFT_CHANNEL)


@command_handler.handle_errors
async def cm_pause(ctx) -> None:
    if not ctx.voice_client:
        await message_handler.send_info(ctx, CONST.MESSAGE_NOTHING_PLAYING)
        return
    if await is_playing(ctx):
        ctx.voice_client.pause()
        await message_handler.send_success(ctx, CONST.MESSAGE_PAUSED_SONG)
    elif ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await message_handler.send_success(ctx, CONST.MESSAGE_RESUMED_SONG)
    else:
        await message_handler.send_info(ctx, CONST.MESSAGE_NOTHING_PLAYING)


@command_handler.handle_errors
async def cm_help(ctx) -> None:
    embed_dict = CONST.get_help_embed()
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
    # Not cm_leave, its reply would follow the restart message
    await leave_voice_channel(ctx)
    await musicbot.client.close()


@command_handler.handle_errors
async def cm_clear_cache(ctx) -> None:
    await ctx.defer()
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
