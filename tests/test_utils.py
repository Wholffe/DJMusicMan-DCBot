import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

import sys
sys.path.append("..")

from music_bot.config import FFMPEG_OPTIONS
from music_bot.utils import *


class TestMusicBotUtils(unittest.TestCase):

    @patch('music_bot.utils.yt_dlp.YoutubeDL.extract_info',
           new_callable=MagicMock)
    async def test_get_info_success(self, mock_extract_info):
        search = "test search"
        mock_extract_info.return_value = {
            "url": "test_url",
            "title": "test_title"
        }

        info = await get_info(search)

        self.assertIsNotNone(info)
        mock_extract_info.assert_called_once_with(search, download=False)

    @patch('music_bot.utils.discord.FFmpegOpusAudio.from_probe',
           new_callable=AsyncMock)
    @patch('music_bot.utils.play_next', new_callable=AsyncMock)
    async def test_play_next(self, mock_from_probe):
        queue = [("url1", "title1")]
        ctx = MagicMock()
        ctx.voice_client.is_playing.return_value = False
        client = MagicMock()

        await play_next(ctx, queue, client)

        mock_from_probe.assert_called_once_with("url1", **FFMPEG_OPTIONS)
        ctx.voice_client.play.assert_called_once()
        ctx.send.assert_called_once_with("Now playing: title1")

    async def test_join_voice_channel_no_voice_channel(self):
        ctx = MagicMock()
        ctx.author.voice = None

        await join_voice_channel(ctx)

        ctx.send.assert_called_once_with(
            "You are not connected to a voice channel.")

    @patch('music_bot.utils.get_info', new_callable=AsyncMock)
    async def test_add_to_queue(self, mock_get_info):
        ctx = MagicMock()
        queue = []
        search = "test search"
        mock_get_info.return_value = {"url": "test_url", "title": "test_title"}

        await add_to_queue(ctx, search, queue)

        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0], ("test_url", "test_title"))
        ctx.send.assert_called_once_with("Added to queue: test_title")


if __name__ == "__main__":
    asyncio.run(unittest.main())