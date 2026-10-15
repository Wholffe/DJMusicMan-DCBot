from copy import deepcopy
from typing import Final

# region Info
VERSION: Final = "3.0.0"
NAME: Final = "DJ Music Man"
FOOTER: Final = f"{NAME} {VERSION}"

# region Progress
PROGRESS_UPDATE_INTERVAL: Final = 2.0  # seconds between progress message edits

# region Embeds
EMBED_HELP = {
    "title": NAME,
    "description": (
        "All commands are available in the `/` menu. "
        "`<search>` can be a YouTube link, a playlist or search terms."
    ),
    "fields": [
        {
            "name": "Playback",
            "value": (
                "`/play <search>` — Plays a song or playlist from YouTube\n"
                "`/playfirst <search>` — Plays it before the rest of the queue\n"
                "`/pause` — Pauses or resumes playback\n"
                "`/skip` — Skips the current song"
            ),
            "inline": False,
        },
        {
            "name": "Queue",
            "value": (
                "`/queue` — Shows the current queue\n"
                "`/shuffle` — Shuffles the queue\n"
                "`/clear` — Clears the queue\n"
                "`/loop` — Toggles looping of the current song\n"
                "`/remove <position>` — Removes a song from the queue"
            ),
            "inline": False,
        },
        {
            "name": "Other",
            "value": (
                "`/leave` — Disconnects the bot from the voice channel\n"
                "`/clear_cache` — Clears the song cache\n"
                "`/ping` — Shows the bot's latency\n"
                "`/restart` — Restarts the bot"
            ),
            "inline": False,
        },
        {
            "name": "Good to know",
            "value": (
                "- Playlists start as soon as the first song is downloaded, "
                "the rest is added while loading.\n"
                "- `/clear` and `/leave` also stop a playlist that is still loading.\n"
                "- The bot leaves the voice channel after a few minutes without "
                "music, or when a song ends and nobody else is listening."
            ),
            "inline": False,
        },
    ],
    "footer": FOOTER,
}
EMBED_QUEUE = {
    "title": "Current Queue",
    "description": "Here are the listed songs:",
    "fields": [],
    "footer": FOOTER,
}


def get_help_embed():
    return deepcopy(EMBED_HELP)


def get_queue_embed():
    return deepcopy(EMBED_QUEUE)


# region Messages
MESSAGE_RESTARTING_BOT: Final = "Restarting bot, please wait..."
MESSAGE_ADDING_SONGS_STOPPED: Final = "Stopped adding songs to the queue."
MESSAGE_BOT_NOT_IN_VOICE: Final = "I'm not in a voice channel."
MESSAGE_CANNOT_CLEAR_CACHE_WHILE_CONNECTED: Final = (
    "Cannot clear cache while connected to a voice channel."
)
MESSAGE_DOWNLOADING: Final = "Downloading:"
MESSAGE_FAILED_VIDEO_INFO: Final = "Failed to retrieve the video information."
MESSAGE_LEFT_CHANNEL: Final = "Left the voice channel."
MESSAGE_NO_ACTIVITY_TIMEOUT: Final = "Bot idle for too long. Leaving the voice channel."
MESSAGE_NO_USERS_IN_CHANNEL: Final = (
    "No users in the voice channel. Leaving the channel."
)
MESSAGE_NOT_CONNECTED: Final = "You are not connected to a voice channel."
MESSAGE_NOTHING_PLAYING: Final = "Nothing is playing."
MESSAGE_PAUSED_SONG: Final = "Paused the song."
MESSAGE_PONG: Final = "pong"
MESSAGE_QUEUE_CLEARED: Final = "Queue cleared."
MESSAGE_QUEUE_EMPTY_USE_PLAY: Final = "Queue is empty. Use /play to add songs."
MESSAGE_QUEUE_EMPTY: Final = "The queue is empty."
MESSAGE_QUEUE_SHUFFLED: Final = "Queue shuffled."
MESSAGE_RESUMED_SONG: Final = "Resumed the song."
MESSAGE_SKIPPED_SONG: Final = "Skipped the current song."

# region Actions
ACTION_CLEARING_QUEUE: Final = "clearing the queue"
ACTION_FETCHING_VIDEO_INFOS: Final = "fetching video information"
ACTION_PLAYING_SONG: Final = "playing the song"
ACTION_SKIPPING_SONG: Final = "skipping the song"
