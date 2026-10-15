import asyncio
import contextlib
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
    is_bot_only_member_in_vc,
    iter_song_infos,
    play_next,
    play_song,
    start_playback_if_idle,
)

GREEN = discord.Color.from_rgb(67, 181, 129)
RED = discord.Color.from_rgb(240, 71, 71)


def _song(i: int) -> dict[str, str]:
    return {"url": f"url{i}", "title": f"title{i}"}


def _yield_songs(*songs: dict[str, str]):
    """Returns a side effect for iter_song_infos that yields the given songs."""

    async def iter_song_infos(search, progress_hook):
        for song in songs:
            yield song

    return iter_song_infos


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
        # Audio is already playing unless a test says otherwise
        self.ctx.voice_client.is_playing.return_value = True
        self.ctx.voice_client.is_paused.return_value = False
        self.ctx.send = AsyncMock()
        self.queue = MusicQueue()
        self.client = MagicMock()
        self.musicbot = MagicMock()
        self.musicbot.queue = self.queue

    def _start_playing(self, *args) -> None:
        self.ctx.voice_client.is_playing.return_value = True

    def _sent_embed(self) -> discord.Embed:
        return self.ctx.send.call_args[1]["embed"]

    def _fields(self) -> dict[str, str]:
        return {
            str(field.name): str(field.value) for field in self._sent_embed().fields
        }

    def _assert_called_with_progress(self, mock_iter_song_infos, search: str) -> None:
        mock_iter_song_infos.assert_called_once()
        args = mock_iter_song_infos.call_args.args
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

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_multiple_songs(self, mock_iter_song_infos):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1), _song(2))
        self.queue.add_song("url0", "title0")

        result = await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist"
        )

        self.assertTrue(result)
        self._assert_called_with_progress(mock_iter_song_infos, "playlist")
        self.assertEqual(
            [song[1] for song in self.queue.queue], ["title0", "title1", "title2"]
        )
        self.assertEqual(self._sent_embed().description, "Added 2 songs to the queue.")

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_front_keeps_order(self, mock_iter_song_infos):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1), _song(2))
        self.queue.add_song("url0", "title0")

        result = await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist", add_to_front=True
        )

        self.assertTrue(result)
        self.assertEqual(
            [song[1] for song in self.queue.queue], ["title1", "title2", "title0"]
        )
        self.assertEqual(
            self._sent_embed().description, "Added 2 songs to the front of the queue."
        )

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_prefixes_www_youtube_url(
        self, mock_iter_song_infos
    ):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1))

        await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "www.youtube.com/watch?v=a"
        )

        self._assert_called_with_progress(
            mock_iter_song_infos, "https://www.youtube.com/watch?v=a"
        )

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_prefixes_www_youtube_url_case_insensitive(
        self, mock_iter_song_infos
    ):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1))

        await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "WWW.YouTube.com/watch?v=a"
        )

        self._assert_called_with_progress(
            mock_iter_song_infos, "https://WWW.YouTube.com/watch?v=a"
        )

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_keeps_full_url(self, mock_iter_song_infos):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1))

        await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "https://www.youtube.com/watch?v=a"
        )

        self._assert_called_with_progress(
            mock_iter_song_infos, "https://www.youtube.com/watch?v=a"
        )

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_no_songs(self, mock_iter_song_infos):
        mock_iter_song_infos.side_effect = _yield_songs()

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "nothing")

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        embed = self._sent_embed()
        self.assertEqual(embed.description, CONST.MESSAGE_FAILED_VIDEO_INFO)
        self.assertEqual(embed.color, discord.Color.red())

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_finish_edits_instead_of_sending(
        self, mock_iter_song_infos, mock_finish
    ):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1))
        mock_finish.return_value = True

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "song")

        self.assertTrue(result)
        mock_finish.assert_awaited_once_with("Added to the queue: title1", success=True)
        self.ctx.send.assert_not_called()

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_finish_false_sends_success(
        self, mock_iter_song_infos, mock_finish
    ):
        mock_iter_song_infos.side_effect = _yield_songs(_song(1))
        mock_finish.return_value = False

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "song")

        self.assertTrue(result)
        mock_finish.assert_awaited_once_with("Added to the queue: title1", success=True)
        embed = self._sent_embed()
        self.assertEqual(embed.description, "Added to the queue: title1")
        self.assertEqual(embed.color, discord.Color.green())

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_error_finishes_progress_and_reraises(
        self, mock_iter_song_infos, mock_finish
    ):
        async def iter_song_infos(search, progress_hook):
            raise OSError("disk full")
            yield  # makes this an async generator

        mock_iter_song_infos.side_effect = iter_song_infos

        with self.assertRaises(OSError):
            await _add_songs_to_queue(self.ctx, self.queue, self.client, "song")

        mock_finish.assert_awaited_once_with(
            CONST.MESSAGE_FAILED_VIDEO_INFO, success=False
        )
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(self.queue.loading, 0)

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_no_songs_finish_edits_instead_of_sending(
        self, mock_iter_song_infos, mock_finish
    ):
        mock_iter_song_infos.side_effect = _yield_songs()
        mock_finish.return_value = True

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "nothing")

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        mock_finish.assert_awaited_once_with(
            CONST.MESSAGE_FAILED_VIDEO_INFO, success=False
        )
        self.ctx.send.assert_not_called()

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_edits_sent_progress_message(
        self, mock_iter_song_infos
    ):
        sent = MagicMock(spec=discord.Message)
        sent.edit = AsyncMock()

        async def iter_song_infos_with_progress(search, progress):
            progress.message = sent
            yield _song(1)

        mock_iter_song_infos.side_effect = iter_song_infos_with_progress

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "song")

        self.assertTrue(result)
        self.ctx.send.assert_not_called()
        embed = sent.edit.call_args[1]["embed"]
        self.assertEqual(embed.description, "Added to the queue: title1")
        self.assertEqual(embed.color, discord.Color.green())

    @patch("music_bot.utils.play_song", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_starts_playback_before_next_song(
        self, mock_iter_song_infos, mock_play_song
    ):
        self.ctx.voice_client.is_playing.return_value = False
        mock_play_song.side_effect = self._start_playing
        played_before_second_song = []

        async def iter_song_infos(search, progress_hook):
            yield _song(1)
            played_before_second_song.append(mock_play_song.await_count)
            yield _song(2)

        mock_iter_song_infos.side_effect = iter_song_infos

        await _add_songs_to_queue(self.ctx, self.queue, self.client, "playlist")

        self.assertEqual(played_before_second_song, [1])
        mock_play_song.assert_awaited_once_with(
            self.ctx, self.queue, self.client, "url1", "title1"
        )
        self.assertEqual(self.queue.current_song, ("url1", "title1"))
        self.assertEqual(self.queue.queue, [("url2", "title2")])

    @patch("music_bot.utils.play_song", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_front_keeps_order_after_first_song_started(
        self, mock_iter_song_infos, mock_play_song
    ):
        self.ctx.voice_client.is_playing.return_value = False
        mock_play_song.side_effect = self._start_playing
        mock_iter_song_infos.side_effect = _yield_songs(_song(1), _song(2), _song(3))
        self.queue.add_song("url0", "title0")

        await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist", add_to_front=True
        )

        self.assertEqual(self.queue.current_song, ("url1", "title1"))
        self.assertEqual(
            [song[1] for song in self.queue.queue], ["title2", "title3", "title0"]
        )
        self.assertEqual(
            self._sent_embed().description, "Added 3 songs to the front of the queue."
        )

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_clear_while_loading_stops_adding(
        self, mock_iter_song_infos
    ):
        closed = []

        async def iter_song_infos(search, progress_hook):
            try:
                yield _song(1)
                self.queue.clear()
                yield _song(2)
                yield _song(3)
            finally:
                closed.append(True)

        mock_iter_song_infos.side_effect = iter_song_infos

        result = await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist"
        )

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        self.assertEqual(closed, [True])
        self.ctx.send.assert_called_once()
        embed = self._sent_embed()
        self.assertEqual(embed.description, CONST.MESSAGE_ADDING_SONGS_STOPPED)
        self.assertEqual(embed.color, discord.Color.red())

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_leaving_voice_channel_stops_adding(
        self, mock_iter_song_infos
    ):
        async def iter_song_infos(search, progress_hook):
            yield _song(1)
            self.ctx.voice_client = None
            yield _song(2)

        mock_iter_song_infos.side_effect = iter_song_infos

        result = await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist"
        )

        self.assertFalse(result)
        self.assertEqual(self.queue.queue, [("url1", "title1")])
        self.assertEqual(
            self._sent_embed().description, CONST.MESSAGE_ADDING_SONGS_STOPPED
        )

    @patch.object(DownloadProgress, "finish", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_stopped_finish_edits_progress_message(
        self, mock_iter_song_infos, mock_finish
    ):
        async def iter_song_infos(search, progress_hook):
            self.queue.clear()
            yield _song(1)

        mock_iter_song_infos.side_effect = iter_song_infos
        mock_finish.return_value = True

        result = await _add_songs_to_queue(
            self.ctx, self.queue, self.client, "playlist"
        )

        self.assertFalse(result)
        self.assertTrue(self.queue.is_empty())
        mock_finish.assert_awaited_once_with(
            CONST.MESSAGE_ADDING_SONGS_STOPPED, success=False
        )
        self.ctx.send.assert_not_called()

    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_counts_running_load(self, mock_iter_song_infos):
        loading = []

        async def iter_song_infos(search, progress_hook):
            loading.append(self.queue.loading)
            yield _song(1)

        mock_iter_song_infos.side_effect = iter_song_infos

        await _add_songs_to_queue(self.ctx, self.queue, self.client, "song")

        self.assertEqual(loading, [1])
        self.assertEqual(self.queue.loading, 0)

    @patch("music_bot.utils.idle_timer.handle_idle", new_callable=AsyncMock)
    @patch("music_bot.utils.play_song", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_song_ending_while_loading_defers_idle(
        self, mock_iter_song_infos, mock_play_song, mock_handle_idle
    ):
        self.ctx.voice_client.is_playing.return_value = False
        idle_calls_while_loading = []

        async def iter_song_infos(search, progress_hook):
            yield _song(1)
            # Song 1 ends while the rest of the playlist is still loading
            await start_playback_if_idle(self.ctx, self.queue, self.client)
            idle_calls_while_loading.append(mock_handle_idle.await_count)

        mock_iter_song_infos.side_effect = iter_song_infos

        await _add_songs_to_queue(self.ctx, self.queue, self.client, "playlist")

        self.assertEqual(idle_calls_while_loading, [0])
        mock_play_song.assert_awaited_once()
        mock_handle_idle.assert_awaited_once_with(self.ctx)

    @patch("music_bot.utils.idle_timer.handle_idle", new_callable=AsyncMock)
    @patch("music_bot.utils.iter_song_infos")
    async def test_add_songs_to_queue_without_songs_after_song_ended_starts_idle(
        self, mock_iter_song_infos, mock_handle_idle
    ):
        self.ctx.voice_client.is_playing.return_value = False
        self.queue.current_song = ("url0", "title0")
        idle_calls_while_loading = []

        async def iter_song_infos(search, progress_hook):
            # The playing song ends while the search is still loading
            await start_playback_if_idle(self.ctx, self.queue, self.client)
            idle_calls_while_loading.append(mock_handle_idle.await_count)
            return
            yield  # makes this an async generator

        mock_iter_song_infos.side_effect = iter_song_infos

        result = await _add_songs_to_queue(self.ctx, self.queue, self.client, "nothing")

        self.assertFalse(result)
        self.assertEqual(idle_calls_while_loading, [0])
        mock_handle_idle.assert_awaited_once_with(self.ctx)
        self.assertEqual(
            self._sent_embed().description, CONST.MESSAGE_FAILED_VIDEO_INFO
        )

    @patch("music_bot.utils.cache_manager")
    async def test_iter_song_infos_yields_songs_in_order(self, mock_cache_manager):
        mock_cache_manager.iter_songs.return_value = (
            song for song in [_song(1), _song(2)]
        )
        hook = MagicMock()

        songs = [song async for song in iter_song_infos("search", hook)]

        mock_cache_manager.iter_songs.assert_called_once_with("search", hook)
        self.assertEqual(songs, [_song(1), _song(2)])

    @patch("music_bot.utils.cache_manager")
    async def test_iter_song_infos_without_songs_ends_cleanly(self, mock_cache_manager):
        mock_cache_manager.iter_songs.return_value = (song for song in [])

        songs = [song async for song in iter_song_infos("search")]

        mock_cache_manager.iter_songs.assert_called_once_with("search", None)
        self.assertEqual(songs, [])

    @patch("music_bot.utils.cache_manager")
    async def test_iter_song_infos_closed_early_closes_sync_generator(
        self, mock_cache_manager
    ):
        requested = []
        closed = []

        def iter_songs():
            try:
                for i in (1, 2):
                    requested.append(i)
                    yield _song(i)
            finally:
                closed.append(True)

        # The mock keeps a reference, so only an explicit close runs the finally
        mock_cache_manager.iter_songs.return_value = iter_songs()

        async with contextlib.aclosing(iter_song_infos("search")) as songs:
            async for _ in songs:
                break

        self.assertEqual(requested, [1])
        self.assertEqual(closed, [True])

    @patch("music_bot.utils.cache_manager")
    async def test_iter_song_infos_propagates_error(self, mock_cache_manager):
        def iter_songs():
            raise OSError("disk full")
            yield  # makes this a generator

        mock_cache_manager.iter_songs.return_value = iter_songs()

        with self.assertRaises(OSError):
            [song async for song in iter_song_infos("search")]

    @patch("music_bot.utils.play_next", new_callable=AsyncMock)
    async def test_start_playback_if_idle_while_playing_does_nothing(
        self, mock_play_next
    ):
        await start_playback_if_idle(self.ctx, self.queue, self.client)

        mock_play_next.assert_not_called()

    @patch("music_bot.utils.play_next", new_callable=AsyncMock)
    async def test_start_playback_if_idle_while_paused_does_nothing(
        self, mock_play_next
    ):
        self.ctx.voice_client.is_playing.return_value = False
        self.ctx.voice_client.is_paused.return_value = True

        await start_playback_if_idle(self.ctx, self.queue, self.client)

        mock_play_next.assert_not_called()

    @patch("music_bot.utils.play_next", new_callable=AsyncMock)
    async def test_start_playback_if_idle_when_idle_plays_next(self, mock_play_next):
        self.ctx.voice_client.is_playing.return_value = False

        await start_playback_if_idle(self.ctx, self.queue, self.client)

        mock_play_next.assert_awaited_once_with(self.ctx, self.queue, self.client)

    @patch("music_bot.utils.play_next", new_callable=AsyncMock)
    async def test_start_playback_if_idle_concurrent_calls_play_next_once(
        self, mock_play_next
    ):
        self.ctx.voice_client.is_playing.return_value = False

        async def play_next(ctx, queue, client):
            await asyncio.sleep(0)  # gives the other call a chance to run
            self._start_playing()

        mock_play_next.side_effect = play_next

        await asyncio.gather(
            start_playback_if_idle(self.ctx, self.queue, self.client),
            start_playback_if_idle(self.ctx, self.queue, self.client),
        )

        mock_play_next.assert_awaited_once_with(self.ctx, self.queue, self.client)

    @patch("music_bot.utils.start_playback_if_idle", new_callable=MagicMock)
    @patch("discord.FFmpegOpusAudio.from_probe", new_callable=AsyncMock)
    async def test_play_song_after_callback_starts_playback_if_idle(
        self, mock_from_probe, mock_start_playback_if_idle
    ):
        await play_song(self.ctx, self.queue, self.client, "url1", "title1")
        after = self.ctx.voice_client.play.call_args.kwargs["after"]

        # discord.py calls after from its player thread, not from the event loop
        with patch(
            "music_bot.utils.asyncio.run_coroutine_threadsafe"
        ) as mock_run_coroutine_threadsafe:
            after(None)

        mock_start_playback_if_idle.assert_called_once_with(
            self.ctx, self.queue, self.client
        )
        mock_run_coroutine_threadsafe.assert_called_once_with(
            mock_start_playback_if_idle.return_value, self.client.loop
        )
        self.client.loop.create_task.assert_not_called()

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
        await play_next(self.ctx, self.queue, self.client)

        mock_handle_idle.assert_called_once_with(self.ctx)
        self.ctx.voice_client.play.assert_not_called()

    @patch("music_bot.utils.idle_timer.handle_idle", new_callable=AsyncMock)
    async def test_play_next_with_empty_queue_while_loading_skips_idle_handling(
        self, mock_handle_idle
    ):
        self.queue.loading = 1

        await play_next(self.ctx, self.queue, self.client)

        mock_handle_idle.assert_not_called()
        self.ctx.voice_client.play.assert_not_called()


if __name__ == "__main__":
    unittest.main()
