from copy import deepcopy
from typing import Final

# region Info
VERSION: Final = "2.2.8"
NAME: Final = "DJ Music Man"
FOOTER: Final = f"{NAME} {VERSION}"

# region Embeds
EMBED_DJHELP = {
    "title": f"{NAME} Help",
    "description": "Here are the available commands:",
    "fields": [
        {"name": "🎶 **Music playback**", "value": "", "inline": False},
        {
            "name": "/play <search>",
            "value": "Plays a song from YouTube",
            "inline": True,
        },
        {
            "name": "/playfirst <search>",
            "value": "Plays a song from YouTube and adds it to the top of the queue",
            "inline": True,
        },
        {
            "name": "/toggle | /pause",
            "value": "Toggle pause|continue playback",
            "inline": True,
        },
        {"name": "/skip", "value": "Skips the current song.", "inline": True},
        {"name": "🛠️ **Queue-Management**", "value": "", "inline": False},
        {
            "name": "/showq | /queue",
            "value": "Shows the current queue.",
            "inline": True,
        },
        {"name": "/shuffle", "value": "Shuffles the queue.", "inline": True},
        {"name": "/clear", "value": "Clears the queue.", "inline": True},
        {
            "name": "/loop",
            "value": "Toggles looping of the current song",
            "inline": True,
        },
        {
            "name": "/rm <index>",
            "value": "Removes a song from the queue",
            "inline": True,
        },
        {"name": "⚙️ **Other commands**", "value": "", "inline": False},
        {
            "name": "/leave",
            "value": "Disconnects the bot from the voice channel",
            "inline": True,
        },
        {"name": "/clear_cache", "value": "Clears the song cache", "inline": True},
        {"name": "/ping", "value": "Ping the bot", "inline": True},
        {"name": "/reset | /restart", "value": "Resets the bot", "inline": True},
    ],
    "footer": FOOTER,
}
EMBED_QUEUE = {
    "title": "Current Queue",
    "description": "Here are the listed songs:",
    "fields": [],
    "footer": FOOTER,
}


def get_djhelp_embed():
    return deepcopy(EMBED_DJHELP)


def get_queue_embed():
    return deepcopy(EMBED_QUEUE)


# region Messages
MESSAGE_RESTARTING_BOT: Final = "Restarting bot, please wait..."
MESSAGE_CANNOT_CLEAR_CACHE_WHILE_CONNECTED: Final = (
    "Cannot clear cache while connected to a voice channel."
)
MESSAGE_FAILED_VIDEO_INFO: Final = "Failed to retrieve the video information."
MESSAGE_NO_ACTIVITY_TIMEOUT: Final = "Bot idle for too long. Leaving the voice channel."
MESSAGE_NO_USERS_IN_CHANNEL: Final = (
    "No users in the voice channel. Leaving the channel."
)
MESSAGE_NOT_CONNECTED: Final = "You are not connected to a voice channel."
MESSAGE_PAUSED_SONG: Final = "Paused the song."
MESSAGE_PONG: Final = "pong"
MESSAGE_QUEUE_CLEARED: Final = "Queue cleared."
MESSAGE_QUEUE_EMPTY_USE_PLAY: Final = "Queue is empty. Use /play to add songs."
MESSAGE_QUEUE_EMPTY: Final = "The queue is empty."
MESSAGE_QUEUE_SHUFFLED: Final = "Queue shuffeled."
MESSAGE_RESUMED_SONG: Final = "Resumed the song."
MESSAGE_SKIPPED_SONG: Final = "Skipped the current song."

# region Actions
ACTION_CLEARING_QUEUE: Final = "clearing the queue"
ACTION_FETCHING_VIDEO_INFOS: Final = "fetching video information"
ACTION_PLAYING_SONG: Final = "playing the song"
ACTION_SKIPPING_SONG: Final = "skipping the song"
