import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

from music_bot.core import MusicBot

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

class TestMusicBot(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bot = commands.Bot(command_prefix='/', intents=intents)
        self.musicbot = MusicBot(self.bot)
        self.ctx = MagicMock()
        self.ctx.send = AsyncMock()
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.stop = AsyncMock()
        self.ctx.voice_client.pause = AsyncMock()
        self.ctx.voice_client.resume = AsyncMock()
        self.ctx.voice_client.is_playing = MagicMock(return_value=True)
        self.musicbot.queue = []

    @patch('music_bot.core.add_to_queue', new_callable=AsyncMock)
    @patch('music_bot.core.join_voice_channel', new_callable=AsyncMock)
    @patch('music_bot.core.play_next', new_callable=AsyncMock)
    async def test_play_command(self, mock_play_next, mock_join_voice_channel, mock_add_to_queue):
        self.ctx.voice_client.is_playing.return_value = False
        
        await self.musicbot.play(self.musicbot, self.ctx, search="test search")
        
        mock_join_voice_channel.assert_called_once_with(self.ctx)
        mock_add_to_queue.assert_called_once_with(self.ctx, "test search", self.musicbot.queue)
        mock_play_next.assert_called_once_with(self.ctx, self.musicbot.queue, self.bot)

    async def test_skip_command(self):
        self.ctx.voice_client.is_playing.return_value = True

        await self.musicbot.skip(self.musicbot, self.ctx)
        
        self.ctx.voice_client.stop.assert_called_once()
        self.ctx.send.assert_called_once_with("Skipped the current song.")

    async def test_ping_command(self):
        await self.musicbot.ping(self.musicbot, self.ctx)
        
        self.ctx.send.assert_called_once_with("pong")

    async def test_clear_command(self):
        self.musicbot.queue.append(("url", "title"))
        
        await self.musicbot.clear(self.musicbot, self.ctx)
        
        self.assertEqual(len(self.musicbot.queue), 0)
        self.ctx.send.assert_called_once_with("Queue cleared.")

    async def test_showq_command_empty(self):
        await self.musicbot.showq(self.musicbot, self.ctx)
        
        self.ctx.send.assert_called_once_with("The queue is empty.")

    async def test_showq_command_with_items(self):
        self.musicbot.queue.append(("url1", "title1"))
        self.musicbot.queue.append(("url2", "title2"))

        await self.musicbot.showq(self.musicbot, self.ctx)
        
        self.ctx.send.assert_any_call("Queue:\n1. title1\n2. title2\n")

    async def test_toggle_command_pause(self):
        self.ctx.voice_client.is_playing.return_value = True

        await self.musicbot.toggle(self.musicbot, self.ctx)
        
        self.ctx.voice_client.pause.assert_called_once()

    async def test_toggle_command_continue(self):
        self.ctx.voice_client.is_playing.return_value = False
        
        await self.musicbot.toggle(self.musicbot, self.ctx)
        
        self.ctx.voice_client.resume.assert_called_once()

if __name__ == "__main__":
    unittest.main()