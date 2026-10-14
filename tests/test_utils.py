import asyncio
import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

import music_bot.constants as CONST
import music_bot.utils as utils
from music_bot.music_queue import MusicQueue
from music_bot.progressbar import DownloadProgress
from music_bot.utils import (
    _add_songs_to_queue,
    cm_showq,
    get_latency_color,
    get_song_infos,
    is_bot_only_member_in_vc,
    play_next,
)

GREEN = discord.Color.from_rgb(67, 181, 129)
RED = discord.Color.from_rgb(240, 71, 71)


class TestGetLatencyColor(unittest.TestCase):
    def test_zero_latency_is_green(self):
        self.assertEqual(get_latency_color(0), GREEN)

    def test_max_latency_is_red(self):
        self.assertEqual(get_latency_color(500), RED)

    def test_latency_above_max_is_clamped_to_red(self):
        self.assertEqual(get_latency_color(1500), RED)

    def test_negative_latency_is_clamped_to_green(self):
        self.assertEqual(get_latency_color(-50), GREEN)

    def test_half_latency_interpolates(self):
        self.assertEqual(get_latency_color(250), discord.Color.from_rgb(153, 126, 100))


class TestUtilsHelpers(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logging.getLogger("MusicBot").setLevel(logging.CRITICAL + 1)
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()
        self.ctx.send = AsyncMock()
        self.queue = MusicQueue()
        self.musicbot = MagicMock()
        self.musicbot.queue = self.queue

    def _sent_embed(self) -> discord.Embed:
        return self.ctx.send.call_args[1]["embed"]

    def _fields(self) -> dict[str, str]:
        return {
            str(field.name): str(field.value) for field in self._sent_embed().fields
        }

    def _assert_called_with_progress(self, mock_get_song_infos, search: str) -> None:
        mock_get_song_infos.assert_called_once()
        args = mock_get_song_infos.call_args.args
        self.assertEqual(args[0], search)
        self.assertIsInstance(args[1], DownloadProgress)
        self.assertIs(args[1].message_handler, utils.message_handler)
        self.assertIs(args[1].ctx, self.ctx)
        self.assertIs(args[1].loop, asyncio.get_running_loop())

    async def test_is_bot_only_member_in_vc_alone(self):
        self.ctx.voice_client.channel.members = [MagicMock()]

        self.assertTrue(await is_bot_only_member_in_vc(self.ctx))

    async def test_is_bot_only_member_in_vc_with_other_members(self):
        self.ctx.voice_client.channel.members = [MagicMock(), MagicMock()]

        self.assertFalse(await is_bot_only_member_in_vc(self.ctx))

    async def test_is_bot_only_member_in_vc_without_voice_client(self):
        self.ctx.voice_client = None

        self.assertFalse(await is_bot_only_member_in_vc(self.ctx))

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_multiple_songs(self, mock_get_song_infos):
        mock_get_song_infos.return_value = [
            {"url": "url1", "title": "title1"},
            {"url": "url2", "title": "title2"},
        ]
        self.queue.add_song("url0", "title0")

        result = await _add_songs_to_queue(self.ctx, self.queue, "playlist")

        self.assertTrue(result)
        self._assert_called_with_progress(mock_get_song_infos, "playlist")
        self.assertEqual(
            [song[1] for song in self.queue.queue], ["title0", "title1", "title2"]
        )
        self.assertEqual(self._sent_embed().description, "Added 2 songs to the queue.")

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_front_keeps_order(self, mock_get_song_infos):
        mock_get_song_infos.return_value = [
            {"url": "url1", "title": "title1"},
            {"url": "url2", "title": "title2"},
        ]
        self.queue.add_song("url0", "title0")

        result = await _add_songs_to_queue(
            self.ctx, self.queue, "playlist", add_to_front=True
        )

        self.assertTrue(result)
        self.assertEqual(
            [song[1] for song in self.queue.queue], ["title1", "title2", "title0"]
        )
        self.assertEqual(
            self._sent_embed().description, "Added 2 songs to the front of the queue."
        )

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_prefixes_www_youtube_url(
        self, mock_get_song_infos
    ):
        mock_get_song_infos.return_value = [{"url": "url1", "title": "title1"}]

        await _add_songs_to_queue(self.ctx, self.queue, "www.youtube.com/watch?v=a")

        self._assert_called_with_progress(
            mock_get_song_infos, "https://www.youtube.com/watch?v=a"
        )

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_prefixes_www_youtube_url_case_insensitive(
        self, mock_get_song_infos
    ):
        mock_get_song_infos.return_value = [{"url": "url1", "title": "title1"}]

        await _add_songs_to_queue(self.ctx, self.queue, "WWW.YouTube.com/watch?v=a")

        self._assert_called_with_progress(
            mock_get_song_infos, "https://WWW.YouTube.com/watch?v=a"
        )

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_keeps_full_url(self, mock_get_song_infos):
        mock_get_song_infos.return_value = [{"url": "url1", "title": "title1"}]

        await _add_songs_to_queue(
            self.ctx, self.queue, "https://www.youtube.com/watch?v=a"
        )

        self._assert_called_with_progress(
            mock_get_song_infos, "https://www.youtube.com/watch?v=a"
        )

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_no_songs(self, mock_get_song_infos):
        mock_get_song_infos.return_value = []

        result = await _add_songs_to_queue(self.ctx, self.queue, "nothing")

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        embed = self._sent_embed()
        self.assertEqual(embed.description, CONST.MESSAGE_FAILED_VIDEO_INFO)
        self.assertEqual(embed.color, discord.Color.red())

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_finish_edits_instead_of_sending(
        self, mock_get_song_infos, mock_finish
    ):
        mock_get_song_infos.return_value = [{"url": "url1", "title": "title1"}]
        mock_finish.return_value = True

        result = await _add_songs_to_queue(self.ctx, self.queue, "song")

        self.assertTrue(result)
        mock_finish.assert_awaited_once_with("Added to the queue: title1", success=True)
        self.ctx.send.assert_not_called()

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_finish_false_sends_success(
        self, mock_get_song_infos, mock_finish
    ):
        mock_get_song_infos.return_value = [{"url": "url1", "title": "title1"}]
        mock_finish.return_value = False

        result = await _add_songs_to_queue(self.ctx, self.queue, "song")

        self.assertTrue(result)
        mock_finish.assert_awaited_once_with("Added to the queue: title1", success=True)
        embed = self._sent_embed()
        self.assertEqual(embed.description, "Added to the queue: title1")
        self.assertEqual(embed.color, discord.Color.green())

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_error_finishes_progress_and_reraises(
        self, mock_get_song_infos, mock_finish
    ):
        mock_get_song_infos.side_effect = OSError("disk full")

        with self.assertRaises(OSError):
            await _add_songs_to_queue(self.ctx, self.queue, "song")

        mock_finish.assert_awaited_once_with(
            CONST.MESSAGE_FAILED_VIDEO_INFO, success=False
        )
        self.assertTrue(self.queue.is_empty())

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_no_songs_finish_edits_instead_of_sending(
        self, mock_get_song_infos, mock_finish
    ):
        mock_get_song_infos.return_value = []
        mock_finish.return_value = True

        result = await _add_songs_to_queue(self.ctx, self.queue, "nothing")

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        mock_finish.assert_awaited_once_with(
            CONST.MESSAGE_FAILED_VIDEO_INFO, success=False
        )
        self.ctx.send.assert_not_called()

    @patch("music_bot.utils.get_song_infos", new_callable=AsyncMock)
    async def test_add_songs_to_queue_edits_sent_progress_message(
        self, mock_get_song_infos
    ):
        sent = MagicMock(spec=discord.Message)
        sent.edit = AsyncMock()

        async def get_song_infos_with_progress(search, progress):
            progress.message = sent
            return [{"url": "url1", "title": "title1"}]

        mock_get_song_infos.side_effect = get_song_infos_with_progress

        result = await _add_songs_to_queue(self.ctx, self.queue, "song")

        self.assertTrue(result)
        self.ctx.send.assert_not_called()
        embed = sent.edit.call_args[1]["embed"]
        self.assertEqual(embed.description, "Added to the queue: title1")
        self.assertEqual(embed.color, discord.Color.green())

    @patch("music_bot.utils.cache_manager")
    async def test_get_song_infos_passes_progress_hook(self, mock_cache_manager):
        mock_cache_manager.get_songs.return_value = [{"url": "u", "title": "t"}]
        hook = MagicMock()

        songs = await get_song_infos("search", hook)

        mock_cache_manager.get_songs.assert_called_once_with(
            "search", progress_hook=hook
        )
        self.assertEqual(songs, [{"url": "u", "title": "t"}])

    @patch("music_bot.utils.cache_manager")
    async def test_get_song_infos_without_hook_passes_none(self, mock_cache_manager):
        mock_cache_manager.get_songs.return_value = []

        await get_song_infos("search")

        mock_cache_manager.get_songs.assert_called_once_with(
            "search", progress_hook=None
        )

    @patch("music_bot.utils.cache_manager")
    async def test_get_song_infos_list_passes_hook_for_each_search(
        self, mock_cache_manager
    ):
        mock_cache_manager.get_songs.side_effect = lambda search, progress_hook: [
            {"url": search, "title": search}
        ]
        hook = MagicMock()

        songs = await get_song_infos(["a", "b"], hook)

        self.assertEqual([song["title"] for song in songs], ["a", "b"])
        self.assertEqual(
            sorted(c.args[0] for c in mock_cache_manager.get_songs.call_args_list),
            ["a", "b"],
        )
        for call in mock_cache_manager.get_songs.call_args_list:
            self.assertIs(call.kwargs["progress_hook"], hook)

    async def test_showq_with_current_song_and_empty_queue(self):
        self.queue.add_song("url1", "title1")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        self.ctx.send.assert_called_once()
        self.assertEqual(
            self._fields(),
            {
                "Now Playing": "Current song: title1",
                "Loop Status": "Disabled",
                "Queue": CONST.MESSAGE_QUEUE_EMPTY,
            },
        )

    async def test_showq_with_upcoming_songs_and_loop(self):
        self.queue.add_song("url1", "title1")
        self.queue.add_song("url2", "title2")
        self.queue.add_song("url3", "title3")
        self.queue.get_next_song()
        self.queue.set_loop(True)

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertEqual(fields["Loop Status"], "Enabled")
        self.assertEqual(fields["Up Next"], "1. title2\n2. title3")
        self.assertNotIn("And more...", fields)
        self.assertNotIn("Queue", fields)

    async def test_showq_with_too_many_songs_shows_remaining(self):
        self.queue.add_song("url0", "title0")
        for i in range(100):
            self.queue.add_song(f"url{i}", "x" * 20)
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertEqual(len(fields["Up Next"].splitlines()), 33)
        self.assertEqual(fields["And more..."], "67 more items")

    async def test_showq_with_too_long_first_title_shows_remaining(self):
        self.queue.add_song("url0", "title0")
        self.queue.add_song("url1", "x" * 800)
        self.queue.add_song("url2", "title2")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertNotIn("Up Next", fields)
        self.assertNotIn("Queue", fields)
        self.assertEqual(fields["And more..."], "2 more items")

    async def test_showq_does_not_modify_queue_embed_template(self):
        self.queue.add_song("url1", "title1")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)
        self.ctx.send.reset_mock()
        await cm_showq(self.musicbot, self.ctx)

        self.assertEqual(len(self._sent_embed().fields), 3)

    @patch("music_bot.utils.idle_timer.handle_idle", new_callable=AsyncMock)
    async def test_play_next_with_empty_queue_starts_idle_handling(
        self, mock_handle_idle
    ):
        await play_next(self.ctx, self.queue, MagicMock())

        mock_handle_idle.assert_called_once_with(self.ctx)
        self.ctx.voice_client.play.assert_not_called()


if __name__ == "__main__":
    unittest.main()
