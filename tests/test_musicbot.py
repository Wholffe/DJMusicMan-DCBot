import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

import music_bot.constants as CONST
from music_bot.core import MusicBot
from music_bot.message_handler import MessageHandler
from music_bot.music_queue import MusicQueue
from music_bot.idle_timer import IdleTimer

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


class TestMusicBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.bot = commands.Bot(command_prefix='/', intents=intents)
        self.musicbot = MusicBot(self.bot)
        self.message_handler = MessageHandler()
        self.idle_timer = IdleTimer()
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
    @patch('music_bot.utils.get_song_infos', new_callable=AsyncMock)
    @patch('music_bot.utils.join_voice_channel', new_callable=AsyncMock)
    async def test_cm_play(self, mock_join_voice_channel, mock_get_song_infos, mock_play_next, mock_is_playing):
        mock_join_voice_channel.return_value = True
        mock_get_song_infos.return_value = [{'url': 'test_url', 'title': 'Test Song'}]
        mock_is_playing.return_value = False

        command = self.bot.get_command('play')
        await command(self.ctx, search='test search')

        mock_join_voice_channel.assert_called_once_with(self.ctx)
        mock_get_song_infos.assert_called_once_with('test search')
        mock_play_next.assert_called_once_with(self.ctx, self.musicbot.queue, self.musicbot.client)
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_success} Added to queue: Test Song')

    async def test_skip_command(self):
        self.ctx.voice_client.is_playing.return_value = True

        command = self.bot.get_command('skip')
        await command(self.ctx)

        self.ctx.voice_client.stop.assert_called_once()
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_success} {CONST.MESSAGE_SKIPPED_SONG}')

    async def test_ping_command(self):
        command = self.bot.get_command('ping')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_info} {CONST.MESSAGE_PONG}')

    async def test_djhelp_command(self):
        command = self.bot.get_command('djhelp')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_info} {CONST.MESSAGE_HELP}')

    async def test_clear_command(self):
        self.musicbot.queue.add_song('url1', 'title1')

        command = self.bot.get_command('clear')
        await command(self.ctx)

        self.assertEqual(len(self.musicbot.queue.queue), 0)
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_success} {CONST.MESSAGE_QUEUE_CLEARED}')

    async def test_showq_command_empty(self):
        command = self.bot.get_command('showq')
        await command(self.ctx)

        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_info} {CONST.MESSAGE_QUEUE_EMPTY}')

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

    @patch('music_bot.idle_timer.asyncio.sleep', new_callable=AsyncMock)
    async def test_idle_timer_disconnects_after_timeout(self, mock_sleep):
        self.idle_timer.max_duration_timeout = 3
        self.ctx.voice_client.is_playing.return_value = False

        await self.idle_timer.start_idle_timer(self.ctx)

        self.ctx.voice_client.disconnect.assert_called_once()
        self.ctx.send.assert_called_once_with(f'{self.message_handler.prefix_info} {CONST.MESSAGE_NO_ACTIVITY_TIMEOUT}')

    @patch('music_bot.idle_timer.asyncio.sleep', new_callable=AsyncMock)
    async def test_idle_timer_resets_if_music_plays(self, mock_sleep):
        self.idle_timer.max_duration_timeout = 3
        self.ctx.voice_client.is_playing.side_effect = [False, True]

        await self.idle_timer.start_idle_timer(self.ctx)

        self.ctx.voice_client.disconnect.assert_not_called()
        self.ctx.send.assert_not_called()

if __name__ == '__main__':
    unittest.main()