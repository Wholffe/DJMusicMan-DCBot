import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

import music_bot.constants as CONST
from music_bot.core import MusicBot
from music_bot.message_handler import MessageHandler
from music_bot.music_queue import MusicQueue

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class TestMusicBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = commands.Bot(command_prefix='/', intents=intents)
        self.musicbot = MusicBot(self.bot)
        self.message_handler = MessageHandler()
        await self.bot.add_cog(self.musicbot)

        self.ctx = MagicMock()
        self.ctx.author.voice = MagicMock()
        self.ctx.author.voice.channel = MagicMock()
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()
        self.ctx.voice_client.stop = MagicMock()
        self.ctx.voice_client.pause = AsyncMock()
        self.ctx.voice_client.resume = AsyncMock()
        self.ctx.voice_client.is_playing = MagicMock(return_value=True)
        self.ctx.send = AsyncMock()
        self.musicbot.queue = MusicQueue()

    @patch('music_bot.utils.is_playing', new_callable=AsyncMock)
    @patch('music_bot.utils.play_next', new_callable=AsyncMock)
    @patch('music_bot.utils.get_info', new_callable=AsyncMock)
    @patch('music_bot.utils.join_voice_channel', new_callable=AsyncMock)
    async def test_cm_play(self,mock_join_voice_channel,mock_get_info,mock_play_next,mock_is_playing):
        mock_join_voice_channel.return_value = True
        mock_get_info.return_value = {'url': 'test_url', 'title': 'Test Song'}
        mock_is_playing.return_value = False

        command = self.bot.get_command('play')
        await command(self.ctx, search='test search')

        mock_join_voice_channel.assert_called_once_with(self.ctx)
        mock_get_info.assert_called_once_with('test search')
        mock_play_next.assert_called_once_with(self.ctx, self.musicbot.queue, self.musicbot.client)
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_success} Added to queue: Test Song')

    @patch('music_bot.utils.get_info', new_callable=AsyncMock)
    async def test_cm_play_with_error(self, mock_get_info):
        mock_get_info.return_value = {'error': 'Test Error'}

        command = self.bot.get_command('play')
        await command(self.ctx, search='test search')

        mock_get_info.assert_called_once_with('test search')
        error_message = 'Error: Test Error'
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_error} {error_message}')

    async def test_skip_command(self):
        self.ctx.voice_client.is_playing.return_value = True

        command = self.bot.get_command('skip')
        await command(self.ctx)

        self.ctx.voice_client.stop.assert_called_once()
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_success} {CONST.MESSAGE_SKIPPED_SONG}')

    async def test_ping_command(self):
        command = self.bot.get_command('ping')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with((f'{self.message_handler.prefix_info} {CONST.MESSAGE_PONG}'))

    async def test_djhelp_command(self):
        command = self.bot.get_command('djhelp')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with((f'{self.message_handler.prefix_info} {CONST.MESSAGE_HELP}'))

    async def test_clear_command(self):
        self.musicbot.queue.add_song('url1', 'title1')

        command = self.bot.get_command('clear')
        await command(self.ctx)

        self.assertEqual(len(self.musicbot.queue.queue), 0)
        self.ctx.send.assert_called_once_with((f'{self.message_handler.prefix_success} {CONST.MESSAGE_QUEUE_CLEARED}'))

    async def test_showq_command_empty(self):
        command = self.bot.get_command('showq')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with((f'{self.message_handler.prefix_info} {CONST.MESSAGE_QUEUE_EMPTY}'))

    async def test_showq_command_with_items(self):
        self.musicbot.queue.add_song('url1', 'title1')
        self.musicbot.queue.add_song('url2', 'title2')

        command = self.bot.get_command('showq')
        await command(self.ctx)

        message = 'Queue:\n1. title1\n2. title2'
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_info} {message}')

    async def test_toggle_command_pause(self):
        self.ctx.voice_client.is_playing.return_value = True

        command = self.bot.get_command('toggle')
        await command(self.ctx)

        self.ctx.voice_client.pause.assert_called_once()

    async def test_toggle_command_continue(self):
        self.ctx.voice_client.is_playing.return_value = False

        command = self.bot.get_command('toggle')
        await command(self.ctx)

        self.ctx.voice_client.resume.assert_called_once()
    
    async def test_leave_command(self):
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()

        command = self.bot.get_command('leave')
        await command(self.ctx)

        self.ctx.voice_client.disconnect.assert_called_once()

if __name__ == '__main__':
    unittest.main()