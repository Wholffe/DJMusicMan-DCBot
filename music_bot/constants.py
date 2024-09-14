from typing import Final

#region Messages
MESSAGE_FAILED_VIDEO_INFO: Final = 'Failed to retrieve the video information.'
MESSAGE_HELP: Final = (
    'Available commands:\n'
    '/clear - Clear the current queue\n'
    '/ping - Ping the bot\n'
    '/play <search> - Play a song from YouTube\n'
    '/showq - Show the current queue\n'
    '/skip - Skip the current song\n'
    '/toggle - Toggle pause|continue playback\n'
)
MESSAGE_NOT_CONNECTED: Final = 'You are not connected to a voice channel.'
MESSAGE_PONG: Final = 'pong'
MESSAGE_QUEUE_EMPTY: Final = 'The queue is empty.'
MESSAGE_QUEUE_EMPTY_USE_PLAY: Final = 'Queue is empty. Use /play to add songs.'
MESSAGE_SKIPPED_SONG: Final = 'Skipped the current song.'
MESSEGE_QUEUE_CLEARED: Final = 'Queue cleared.'

#region Acrions
ACTION_PLAYING_SONG: Final = 'playing the song'
ACTION_SKIPPING_SONG: Final = 'skipping the song'
ACTION_CLEARING_QUEUE: Final = 'clearing the queue'
ACTION_FETCHING_VIDEO_INFOS: Final = 'fetching video information'