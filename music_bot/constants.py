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
    "title": f"{NAME} Help",
    "description": "Here are the available commands:",
    "fields": [
        {"name": "🎶 **Music playback**", "value": "", "inline": False},
        {
            "name": "/play <search>",
            "value": "Plays a song or playlist from YouTube.",
            "inline": True,
        },
        {
            "name": "/playfirst <search>",
            "value": (
                "Plays a song or playlist from YouTube before the rest of the queue."
            ),
            "inline": True,
        },
        {"name": "/pause", "value": "Pauses or resumes playback.", "inline": True},
        {"name": "/skip", "value": "Skips the current song.", "inline": True},
        {"name": "🛠️ **Queue-Management**", "value": "", "inline": False},
        {"name": "/queue", "value": "Shows the current queue.", "inline": True},
        {"name": "/shuffle", "value": "Shuffles the queue.", "inline": True},
        {"name": "/clear", "value": "Clears the queue.", "inline": True},
        {
            "name": "/loop",
            "value": "Toggles looping of the current song.",
            "inline": True,
        },
        {
            "name": "/remove <position>",
            "value": "Removes a song from the queue.",
            "inline": True,
        },
        {"name": "⚙️ **Other commands**", "value": "", "inline": False},
        {
            "name": "/leave",
            "value": "Disconnects the bot from the voice channel.",
            "inline": True,
        },
        {"name": "/clear_cache", "value": "Clears the song cache.", "inline": True},
        {"name": "/ping", "value": "Shows the bot's latency.", "inline": True},
        {"name": "/restart", "value": "Restarts the bot.", "inline": True},
        {"name": "/help", "value": "Shows all commands.", "inline": True},
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
