from typing import Final

#region Info
VERSION: Final = '2.1.3'
NAME: Final = 'DJ Music Man'
FOOTER: Final = f'{NAME} {VERSION}'

#region Embeds
EMBED_DJHELP = {
    "title": f"{NAME} Help",
    "description": "Here are the available commands:",
    "fields": [
        {"name": "🎶 **Music playback**", "value": "", "inline": False},
        {"name": "/play <search>", "value": "Plays a song from YouTube.", "inline": True},
        {"name": "/toggle", "value": "Toggle pause|continue playback", "inline": True},
        {"name": "/skip", "value": "Skips the current song.", "inline": True},

        {"name": "🛠️ **Queue-Management**", "value": "", "inline": False},
        {"name": "/showq", "value": "Shows the current queue.", "inline": True},
        {"name": "/shuffle", "value": "Shuffles the queue.", "inline": True},
        {"name": "/clear", "value": "Clears the queue.", "inline": True},
        {"name": "/loop", "value": "Toggles looping of the current song.", "inline": True},
        {"name": "/rm <index>", "value": "Removes a song from the queue.", "inline": True},
        {"name": " ", "value": " ", "inline": True},

        {"name": "⚙️ **Other commands**", "value": "", "inline": False},
        {"name": "/leave", "value": "Disconnects the bot from the voice channel.", "inline": True},
        {"name": "/ping", "value": "Ping the bot", "inline": True},
        {"name": " ", "value": " ", "inline": True},
    ],
    "footer": FOOTER
}
EMBED_QUEUE = {
    "title": "Current Queue",
    "description": "Here are the listed songs:",
    "fields": [
    ],
    "footer": FOOTER
}
def get_djhelp_embed():
    return EMBED_DJHELP.copy()

def get_queue_embed():
    return EMBED_QUEUE.copy()

#region Messages
MESSAGE_FAILED_VIDEO_INFO: Final = 'Failed to retrieve the video information.'
MESSAGE_HELP: Final = (
    'Available commands:\n'
    '/clear - Clear the current queue\n'
    '/leave - Leave the voice channel'
    '/loop - Toggle loop mode for the current song\n'
    '/ping - Ping the bot\n'
    '/play <search> - Play a song from YouTube\n'
    '/showq - Show the current queue\n'
    '/shuffle - Shuffle the queue order\n'
    '/skip - Skip the current song\n'
    '/toggle - Toggle pause|continue playback\n'
)
MESSAGE_NOT_CONNECTED: Final = 'You are not connected to a voice channel.'
MESSAGE_PONG: Final = 'pong'
MESSAGE_QUEUE_EMPTY: Final = 'The queue is empty.'
MESSAGE_QUEUE_EMPTY_USE_PLAY: Final = 'Queue is empty. Use /play to add songs.'
MESSAGE_SKIPPED_SONG: Final = 'Skipped the current song.'
MESSAGE_QUEUE_CLEARED: Final = 'Queue cleared.'
MESSAGE_QUEUE_SHUFFLED: Final = 'Queue shuffeled.'
MESSAGE_NO_ACTIVITY_TIMEOUT: Final = 'Bot idle for too long. Leaving the voice channel.'
MESSAGE_PAUSED_SONG: Final = 'Paused the song.'
MESSAGE_RESUMED_SONG: Final = 'Resumed the song.'

#region Acrions
ACTION_PLAYING_SONG: Final = 'playing the song'
ACTION_SKIPPING_SONG: Final = 'skipping the song'
ACTION_CLEARING_QUEUE: Final = 'clearing the queue'
ACTION_FETCHING_VIDEO_INFOS: Final = 'fetching video information'