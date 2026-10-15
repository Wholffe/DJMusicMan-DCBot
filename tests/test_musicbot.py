import logging
import unittest
from unittest.mock import ANY, AsyncMock, MagicMock, PropertyMock, patch

import discord
from discord.ext import commands

import music_bot.constants as CONST
import music_bot.services as services
from music_bot.core import MusicBot
from music_bot.idle_timer import IdleTimer
from music_bot.message_handler import MessageHandler
from music_bot.music_queue import MusicQueue
from music_bot.playback import play_next
from music_bot.progressbar import DownloadProgress

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True


def _yield_songs(*songs: dict[str, str]):
    """Returns a side effect for iter_song_infos that yields the given songs."""

    async def iter_song_infos(search, progress_hook):
        for song in songs:
            yield song

    return iter_song_infos


async def _pop_next_song(ctx, queue: MusicQueue, client) -> None:
    """Stands in for play_next, which takes the next song from the queue."""
    queue.get_next_song()


class TestMusicBot(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logging.getLogger("MusicBot").setLevel(logging.CRITICAL + 1)
        self.bot = commands.Bot(command_prefix="/", intents=intents)
        self.musicbot = MusicBot(self.bot)
        self.message_handler = MessageHandler()
        self.idle_timer = IdleTimer(self.message_handler)
        await self.bot.add_cog(self.musicbot)

        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.author = MagicMock()
        self.ctx.author.voice = MagicMock()
        self.ctx.author.voice.channel = MagicMock()
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()
        self.ctx.voice_client.stop = MagicMock()

        self.ctx.voice_client.pause = MagicMock()
        self.ctx.voice_client.resume = MagicMock()

        self.ctx.voice_client.is_playing = MagicMock(return_value=True)
        self.ctx.voice_client.is_paused = MagicMock(return_value=False)
        self.ctx.send = AsyncMock()
        self.ctx.bot = self.bot
        self.musicbot.queue = MusicQueue()

    def _get_command(self, name: str) -> commands.Command:
        command = self.bot.get_command(name)
        assert command is not None, f"Command '{name}' is not registered"
        return command

    def _assert_called_with_progress(self, mock_iter_song_infos, search: str) -> None:
        mock_iter_song_infos.assert_called_once()
        args = mock_iter_song_infos.call_args.args
        self.assertEqual(args[0], search)
        self.assertIsInstance(args[1], DownloadProgress)
        self.assertIs(args[1].message_handler, services.message_handler)

    @patch("music_bot.playback.play_next", new_callable=AsyncMock)
    @patch("music_bot.playback.iter_song_infos")
    @patch("music_bot.playback.join_voice_channel", new_callable=AsyncMock)
    async def test_cm_play(
        self,
        mock_join_voice_channel,
        mock_iter_song_infos,
        mock_play_next,
    ):
        mock_join_voice_channel.return_value = True
        mock_iter_song_infos.side_effect = _yield_songs(
            {"url": "test_url", "title": "Test Song"}
        )
        mock_play_next.side_effect = _pop_next_song
        self.ctx.voice_client.is_playing.return_value = False

        command = self._get_command("play")
        await command(self.ctx, search="test search")

        mock_join_voice_channel.assert_called_once_with(self.musicbot, self.ctx)
        self._assert_called_with_progress(mock_iter_song_infos, "test search")
        mock_play_next.assert_called_once_with(
            self.ctx, self.musicbot.queue, self.musicbot.client
        )
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, "Added to the queue: Test Song")

    @patch("music_bot.playback.play_next", new_callable=AsyncMock)
    @patch("music_bot.playback.iter_song_infos")
    @patch("music_bot.playback.join_voice_channel", new_callable=AsyncMock)
    async def test_cm_play_invalid_url(
        self,
        mock_join_voice_channel,
        mock_iter_song_infos,
        mock_play_next,
    ):
        mock_join_voice_channel.return_value = True
        mock_iter_song_infos.side_effect = _yield_songs()
        self.ctx.voice_client.is_playing.return_value = False

        command = self._get_command("play")
        await command(self.ctx, search="invalid url")

        mock_join_voice_channel.assert_called_once_with(self.musicbot, self.ctx)
        self._assert_called_with_progress(mock_iter_song_infos, "invalid url")
        # Nothing is playing, so play_next runs once to start the idle handling
        mock_play_next.assert_called_once_with(
            self.ctx, self.musicbot.queue, self.musicbot.client
        )
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_FAILED_VIDEO_INFO)

    @patch("music_bot.playback.play_next", new_callable=AsyncMock)
    @patch("music_bot.playback.iter_song_infos")
    @patch("music_bot.playback.join_voice_channel", new_callable=AsyncMock)
    async def test_cm_playfirst(
        self,
        mock_join_voice_channel,
        mock_iter_song_infos,
        mock_play_next,
    ):
        mock_join_voice_channel.return_value = True
        mock_iter_song_infos.side_effect = _yield_songs(
            {"url": "test_url", "title": "Test Song"}
        )
        self.musicbot.queue.add_song("url1", "title1")

        command = self._get_command("playfirst")
        await command(self.ctx, search="test search")

        mock_join_voice_channel.assert_called_once_with(self.musicbot, self.ctx)
        self._assert_called_with_progress(mock_iter_song_infos, "test search")
        self.assertEqual(
            [song[1] for song in self.musicbot.queue.queue], ["Test Song", "title1"]
        )
        mock_play_next.assert_not_called()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(
            embed.description, "Added to the front of the queue: Test Song"
        )

    async def test_skip_command(self):
        self.ctx.voice_client.is_playing.return_value = True
        self.musicbot.queue.loop = True

        command = self._get_command("skip")
        await command(self.ctx)

        self.assertTrue(self.musicbot.queue.loop)
        self.ctx.voice_client.stop.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_SKIPPED_SONG)

    async def test_ping_command(self):
        with patch.object(
            commands.Bot, "latency", new_callable=PropertyMock
        ) as mock_latency:
            mock_latency.return_value = 0.123

            command = self._get_command("ping")
            await command(self.ctx)

            self.ctx.send.assert_called_once()
            embed = self.ctx.send.call_args[1]["embed"]
            self.assertFalse(embed.title)
            self.assertEqual(embed.description, "ping: 123ms")

    async def test_djhelp_command(self):
        command = self._get_command("djhelp")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.title, "DJ Music Man Help")
        self.assertEqual(embed.description, "Here are the available commands:")
        self.assertGreaterEqual(len(embed.fields), 1)

    async def test_clear_command(self):
        self.musicbot.queue.add_song("url1", "title1")

        command = self._get_command("clear")
        await command(self.ctx)

        self.assertEqual(len(self.musicbot.queue.queue), 0)
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_QUEUE_CLEARED)

    async def test_showq_command_empty(self):
        command = self._get_command("showq")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_QUEUE_EMPTY)

    async def test_showq_command_with_items(self):
        self.musicbot.queue.add_song("url1", "title1")
        self.musicbot.queue.add_song("url2", "title2")
        self.musicbot.queue.current_song = self.musicbot.queue.get_next_song()

        command = self._get_command("showq")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.title, "Current Queue")
        self.assertEqual(embed.description, "Here are the listed songs:")
        self.assertGreaterEqual(len(embed.fields), 2)
        self.assertTrue(any(field.name == "Now Playing" for field in embed.fields))
        self.assertTrue(any(field.name == "Loop Status" for field in embed.fields))

    async def test_toggle_command_pause(self):
        self.ctx.voice_client.is_playing.return_value = True
        self.ctx.voice_client.is_paused.return_value = False

        command = self._get_command("toggle")
        await command(self.ctx)

        self.ctx.voice_client.pause.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_PAUSED_SONG)

    async def test_toggle_command_continue(self):
        self.ctx.voice_client.is_playing.return_value = False
        self.ctx.voice_client.is_paused.return_value = True

        command = self._get_command("toggle")
        await command(self.ctx)

        self.ctx.voice_client.resume.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_RESUMED_SONG)

    async def test_toggle_while_idle_sends_nothing_playing(self):
        self.ctx.voice_client.is_playing.return_value = False
        self.ctx.voice_client.is_paused.return_value = False

        command = self._get_command("toggle")
        await command(self.ctx)

        self.ctx.voice_client.resume.assert_not_called()
        self.ctx.voice_client.pause.assert_not_called()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_NOTHING_PLAYING)

    async def test_toggle_without_voice_client_sends_nothing_playing(self):
        self.ctx.voice_client = None

        command = self._get_command("toggle")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_NOTHING_PLAYING)

    async def test_leave_command(self):
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()

        command = self._get_command("leave")
        await command(self.ctx)

        self.ctx.voice_client.disconnect.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_LEFT_CHANNEL)
        self.assertEqual(embed.color, discord.Color.green())

    async def test_leave_without_voice_client_sends_not_in_voice(self):
        self.ctx.voice_client = None

        command = self._get_command("leave")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_BOT_NOT_IN_VOICE)

    @patch("music_bot.idle_timer.asyncio.sleep", new_callable=AsyncMock)
    async def test_idle_timer_disconnects_after_timeout(self, mock_sleep):
        self.idle_timer.MAX_DURATION_TIMEOUT = 3
        self.ctx.voice_client.is_playing.return_value = False

        await self.idle_timer.start_idle_timer(self.ctx)

        self.ctx.voice_client.disconnect.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)

    @patch("music_bot.idle_timer.asyncio.sleep", new_callable=AsyncMock)
    async def test_idle_timer_resets_if_music_plays(self, mock_sleep):
        self.idle_timer.MAX_DURATION_TIMEOUT = 3
        self.ctx.voice_client.is_playing.side_effect = [False, True]

        await self.idle_timer.start_idle_timer(self.ctx)

        self.ctx.voice_client.disconnect.assert_not_called()
        self.ctx.send.assert_not_called()

    @patch("random.shuffle")
    async def test_shuffle_command_calls_random_shuffle(self, mock_shuffle):
        command = self._get_command("shuffle")
        await command(self.ctx)

        mock_shuffle.assert_called_once_with(self.musicbot.queue.queue)
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_QUEUE_SHUFFLED)

    async def test_loop_command_enable(self):
        command = self._get_command("loop")
        await command(self.ctx)

        self.assertTrue(self.musicbot.queue.loop)
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, "Looping is enabled.")

    async def test_loop_command_disable(self):
        self.musicbot.queue.loop = True

        command = self._get_command("loop")
        await command(self.ctx)

        self.assertFalse(self.musicbot.queue.loop)
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, "Looping is disabled.")

    @patch("discord.FFmpegOpusAudio.from_probe", new_callable=AsyncMock)
    async def test_play_next_with_loop(self, mock_from_probe):
        self.musicbot.queue.add_song("url1", "title1")
        self.musicbot.queue.add_song("url2", "title2")
        self.musicbot.queue.loop = True
        self.musicbot.queue.current_song = ("url0", "title0")

        source = MagicMock()
        mock_from_probe.return_value = source

        self.ctx.voice_client.play = MagicMock()

        await play_next(self.ctx, self.musicbot.queue, self.musicbot.client)

        self.assertEqual(self.musicbot.queue.current_song[1], "title0")
        self.assertEqual(len(self.musicbot.queue.queue), 2)
        self.assertEqual(self.musicbot.queue.queue[0][1], "title1")
        self.assertEqual(self.musicbot.queue.queue[1][1], "title2")
        self.ctx.voice_client.play.assert_called_once_with(source, after=ANY)

    async def test_remove_from_queue_valid(self):
        self.musicbot.queue.add_song("url1", "title1")
        self.musicbot.queue.add_song("url2", "title2")

        command = self._get_command("rm")
        await command(self.ctx, 1)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, "Removed from queue: title1")
        self.assertEqual(len(self.musicbot.queue.queue), 1)
        self.assertEqual(self.musicbot.queue.queue[0][1], "title2")

    async def test_remove_from_queue_invalid(self):
        self.musicbot.queue.add_song("url1", "title1")

        command = self._get_command("rm")
        await command(self.ctx, 2)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, "Invalid queue number: 2")
        self.assertEqual(len(self.musicbot.queue.queue), 1)
        self.assertEqual(self.musicbot.queue.queue[0][1], "title1")

    @patch("music_bot.playback.is_bot_only_member_in_vc", new_callable=AsyncMock)
    @patch("music_bot.playback.play_song", new_callable=AsyncMock)
    async def test_play_next_with_other_member_in_vc(
        self, mock_play_song, mock_is_bot_only_member_in_vc
    ):
        self.musicbot.queue.add_song("url1", "title1")
        self.musicbot.queue.add_song("url2", "title2")

        mock_is_bot_only_member_in_vc.return_value = False
        await play_next(self.ctx, self.musicbot.queue, self.musicbot.client)

        self.ctx.voice_client.disconnect.assert_not_called()
        mock_play_song.assert_called_once()

    @patch("music_bot.playback.is_bot_only_member_in_vc", new_callable=AsyncMock)
    async def test_play_next_with_no_other_member_in_vc(
        self, mock_is_bot_only_member_in_vc
    ):
        self.musicbot.queue.add_song("url1", "title1")
        self.musicbot.queue.add_song("url2", "title2")
        self.musicbot.queue.current_song = self.musicbot.queue.get_next_song()

        mock_is_bot_only_member_in_vc.return_value = True
        await play_next(self.ctx, self.musicbot.queue, self.musicbot.client)

        self.ctx.voice_client.disconnect.assert_called_once()
        self.ctx.voice_client.play.assert_not_called()
        self.ctx.send.assert_called()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertFalse(embed.title)
        self.assertEqual(embed.description, CONST.MESSAGE_NO_USERS_IN_CHANNEL)

    async def test_restart_command(self):
        with patch.object(self.bot, "close", new_callable=AsyncMock) as mock_close:
            command = self._get_command("restart")
            await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_RESTARTING_BOT)
        self.ctx.voice_client.disconnect.assert_called_once()
        mock_close.assert_called_once()

    @patch("music_bot.playback.join_voice_channel", new_callable=AsyncMock)
    async def test_play_fails_if_user_not_in_voice_channel(
        self, mock_join_voice_channel
    ):
        mock_join_voice_channel.return_value = False

        command = self._get_command("play")
        await command(self.ctx, search="test search")

        mock_join_voice_channel.assert_called_once_with(self.musicbot, self.ctx)
        self.ctx.send.assert_not_called()

    async def test_skip_when_not_playing(self):
        self.ctx.voice_client.is_playing.return_value = False

        command = self._get_command("skip")
        await command(self.ctx)

        self.ctx.voice_client.stop.assert_not_called()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_NOTHING_PLAYING)

    async def test_skip_without_voice_client_sends_nothing_playing(self):
        self.ctx.voice_client = None

        command = self._get_command("skip")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_NOTHING_PLAYING)

    async def test_skip_when_paused_skips_song(self):
        self.ctx.voice_client.is_playing.return_value = False
        self.ctx.voice_client.is_paused.return_value = True

        command = self._get_command("skip")
        await command(self.ctx)

        self.ctx.voice_client.stop.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_SKIPPED_SONG)

    @patch("music_bot.services.idle_timer.clear_timer_task")
    async def test_command_error_handling(self, mock_clear_timer_task):
        error_message = "A critical failure occurred"
        mock_clear_timer_task.side_effect = Exception(error_message)

        command = self._get_command("leave")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]

        expected_description = f'Command "cm_leave" failed: {error_message}'
        self.assertEqual(embed.description, expected_description)
        self.assertEqual(embed.color, discord.Color.red())

    async def test_shuffle_command_error_is_sent_to_ctx(self):
        error_message = "A critical failure occurred"
        self.musicbot.queue.shuffle_queue = MagicMock(
            side_effect=Exception(error_message)
        )

        command = self._get_command("shuffle")
        await command(self.ctx)

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        expected_description = f'Command "cm_shuffle" failed: {error_message}'
        self.assertEqual(embed.description, expected_description)
        self.assertEqual(embed.color, discord.Color.red())

    @patch("music_bot.playback.join_voice_channel", new_callable=AsyncMock)
    async def test_play_command_error_is_sent_to_ctx(self, mock_join_voice_channel):
        error_message = "A critical failure occurred"
        mock_join_voice_channel.side_effect = Exception(error_message)

        command = self._get_command("play")
        await command(self.ctx, search="test song")

        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]
        expected_description = f'Command "cm_play" failed: {error_message}'
        self.assertEqual(embed.description, expected_description)
        self.assertEqual(embed.color, discord.Color.red())

    @patch("music_bot.services.cache_manager.clear_cache")
    async def test_clear_cache_succeeds_when_disconnected(self, mock_clear_cache):
        self.ctx.voice_client = None
        mock_clear_cache.return_value = (10, 50.5)

        command = self._get_command("clear_cache")
        await command(self.ctx)

        mock_clear_cache.assert_called_once()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]

        self.assertEqual(
            embed.description, "Cleared cache: Deleted 10 files, freeing 50.5 MB."
        )
        self.assertEqual(embed.color, discord.Color.green())

    @patch("music_bot.services.cache_manager.clear_cache")
    async def test_clear_cache_fails_while_connected(self, mock_clear_cache):
        command = self._get_command("clear_cache")
        await command(self.ctx)

        mock_clear_cache.assert_not_called()
        self.ctx.send.assert_called_once()
        embed = self.ctx.send.call_args[1]["embed"]

        self.assertEqual(
            embed.description, CONST.MESSAGE_CANNOT_CLEAR_CACHE_WHILE_CONNECTED
        )
        self.assertEqual(embed.color, discord.Color.red())

    def test_logger_writes_info_message(self):
        from music_bot.logger import logger

        test_message = "test info message"

        with self.assertLogs("MusicBot", level="INFO") as cm:
            logger.info(test_message)

        self.assertIn(test_message, cm.output[0])


if __name__ == "__main__":
    unittest.main()
