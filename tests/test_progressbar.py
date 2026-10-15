import asyncio
import concurrent.futures
import logging
import unittest
from collections.abc import Coroutine
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

import music_bot.constants as CONST
from music_bot.progressbar import DownloadProgress, render_progress_bar

MB = 1024**2


class TestRenderProgressBar(unittest.TestCase):
    def test_render_progress_bar_zero_percent(self):
        self.assertEqual(
            render_progress_bar(0, 4 * MB), "▱" * 20 + "  0%\n0.0 / 4.0 MB"
        )

    def test_render_progress_bar_quarter(self):
        self.assertEqual(
            render_progress_bar(MB, 4 * MB),
            "▰" * 5 + "▱" * 15 + "  25%\n1.0 / 4.0 MB",
        )

    def test_render_progress_bar_sixty_percent(self):
        self.assertEqual(
            render_progress_bar(int(2.4 * MB), 4 * MB),
            "▰" * 12 + "▱" * 8 + "  60%\n2.4 / 4.0 MB",
        )

    def test_render_progress_bar_complete(self):
        self.assertEqual(
            render_progress_bar(4 * MB, 4 * MB), "▰" * 20 + "  100%\n4.0 / 4.0 MB"
        )

    def test_render_progress_bar_without_total_shows_size_only(self):
        self.assertEqual(render_progress_bar(int(2.4 * MB), None), "2.4 MB")

    def test_render_progress_bar_zero_total_shows_size_only(self):
        self.assertEqual(render_progress_bar(int(2.4 * MB), 0), "2.4 MB")

    def test_render_progress_bar_downloaded_above_total_is_clamped(self):
        self.assertEqual(
            render_progress_bar(6 * MB, 4 * MB), "▰" * 20 + "  100%\n6.0 / 4.0 MB"
        )

    def test_render_progress_bar_custom_width(self):
        self.assertEqual(
            render_progress_bar(MB, 2 * MB, width=10),
            "▰" * 5 + "▱" * 5 + "  50%\n1.0 / 2.0 MB",
        )


class TestDownloadProgress(unittest.IsolatedAsyncioTestCase):
    futures: list[concurrent.futures.Future[None]]

    async def asyncSetUp(self):
        logging.getLogger("MusicBot").setLevel(logging.CRITICAL + 1)
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.send = AsyncMock()
        self.loop = asyncio.get_running_loop()
        self.message_handler = MagicMock()
        self.message_handler.send_progress = AsyncMock(
            side_effect=lambda ctx, text: MagicMock(spec=discord.Message)
        )
        self.message_handler.edit_progress = AsyncMock()
        self.message_handler.edit_success = AsyncMock()
        self.message_handler.edit_error = AsyncMock()
        self.progress = DownloadProgress(self.ctx, self.loop, self.message_handler)

        # Collect the scheduled futures so tests can wait for them deterministically
        self.futures = []
        run_threadsafe = asyncio.run_coroutine_threadsafe

        def collect(
            coro: Coroutine[Any, Any, None], loop: asyncio.AbstractEventLoop
        ) -> concurrent.futures.Future[None]:
            future = run_threadsafe(coro, loop)
            self.futures.append(future)
            return future

        patcher = patch(
            "music_bot.progressbar.asyncio.run_coroutine_threadsafe",
            side_effect=collect,
        )
        self.mock_run_threadsafe = patcher.start()
        self.addCleanup(patcher.stop)

        # Patch the module reference only, so loop.time() keeps the real clock
        time_patcher = patch("music_bot.progressbar.time")
        self.mock_time = time_patcher.start()
        self.addCleanup(time_patcher.stop)
        self.mock_time.monotonic.return_value = 100.0

    async def _emit(self, status: dict[str, Any], now: float | None = None) -> None:
        """Calls the hook from a worker thread like yt-dlp does, then waits."""
        if now is not None:
            self.mock_time.monotonic.return_value = now
        await self.loop.run_in_executor(None, self.progress, status)
        for future in self.futures:
            await asyncio.wrap_future(future)

    @staticmethod
    def _status(
        status: str = "downloading",
        title: str | None = "Song",
        downloaded: int | None = MB,
        total: int | None = 4 * MB,
        song_id: str | None = None,
    ) -> dict[str, Any]:
        info_dict: dict[str, Any] = {} if title is None else {"title": title}
        if song_id is not None:
            info_dict["id"] = song_id
        result: dict[str, Any] = {"status": status, "info_dict": info_dict}
        if downloaded is not None:
            result["downloaded_bytes"] = downloaded
        if total is not None:
            result["total_bytes"] = total
        return result

    @staticmethod
    def _text(title: str, downloaded: int, total: int | None) -> str:
        return (
            f"{CONST.MESSAGE_DOWNLOADING} {title}\n"
            f"{render_progress_bar(downloaded, total)}"
        )

    async def test_first_event_sends_progress_message(self):
        await self._emit(self._status())

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song", MB, 4 * MB)
        )
        self.message_handler.edit_progress.assert_not_called()

    async def test_event_after_interval_edits_message(self):
        await self._emit(self._status(), now=100.0)
        sent = self.progress.message

        await self._emit(
            self._status(downloaded=2 * MB), now=100.0 + CONST.PROGRESS_UPDATE_INTERVAL
        )

        self.message_handler.send_progress.assert_awaited_once()
        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 2 * MB, 4 * MB)
        )

    async def test_event_within_interval_is_throttled(self):
        await self._emit(self._status(), now=100.0)

        await self._emit(
            self._status(downloaded=2 * MB),
            now=100.0 + CONST.PROGRESS_UPDATE_INTERVAL / 2,
        )

        self.message_handler.send_progress.assert_awaited_once()
        self.message_handler.edit_progress.assert_not_called()
        self.assertEqual(len(self.futures), 1)

    async def test_total_bytes_estimate_is_used_without_total_bytes(self):
        status = self._status(total=None)
        status["total_bytes_estimate"] = 4 * MB

        await self._emit(status)

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song", MB, 4 * MB)
        )

    async def test_finished_bypasses_throttle_and_shows_complete(self):
        await self._emit(self._status(), now=100.0)
        sent = self.progress.message

        await self._emit(self._status("finished", downloaded=4 * MB), now=100.1)

        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 4 * MB, 4 * MB)
        )
        self.assertIn("100%", self.message_handler.edit_progress.call_args[0][1])

    async def test_finished_without_downloaded_bytes_shows_complete(self):
        await self._emit(self._status(), now=100.0)
        sent = self.progress.message

        await self._emit(self._status("finished", downloaded=None), now=100.1)

        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 4 * MB, 4 * MB)
        )

    async def test_finished_without_total_uses_downloaded_bytes(self):
        await self._emit(self._status(total=None), now=100.0)
        sent = self.progress.message

        await self._emit(
            self._status("finished", downloaded=3 * MB, total=None), now=100.1
        )

        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 3 * MB, 3 * MB)
        )

    async def test_other_status_is_ignored(self):
        await self._emit(self._status("error"))

        self.message_handler.send_progress.assert_not_called()
        self.message_handler.edit_progress.assert_not_called()
        self.assertEqual(self.futures, [])
        self.assertIsNone(self.progress.last_update)

    async def test_new_title_edits_same_message_without_throttle(self):
        await self._emit(self._status(title="First"), now=100.0)
        sent = self.progress.message

        await self._emit(self._status(title="Second"), now=100.1)

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("First", MB, 4 * MB)
        )
        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Second", MB, 4 * MB)
        )

    async def test_new_title_right_after_finished_is_shown(self):
        await self._emit(self._status(title="First"), now=100.0)
        await self._emit(self._status("finished", title="First"), now=100.0)

        await self._emit(self._status(title="Second"), now=100.0)

        self.message_handler.send_progress.assert_awaited_once()
        self.assertEqual(
            self.message_handler.edit_progress.call_args[0][1],
            self._text("Second", MB, 4 * MB),
        )

    async def test_missing_title_uses_unknown_title(self):
        await self._emit(self._status(title=None))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Unknown Title", MB, 4 * MB)
        )

    async def test_finished_without_downloading_is_ignored(self):
        await self._emit(self._status("finished", downloaded=4 * MB))

        self.message_handler.send_progress.assert_not_called()
        self.message_handler.edit_progress.assert_not_called()
        self.assertEqual(self.futures, [])
        self.assertIsNone(self.progress.last_update)

    async def test_same_title_with_different_ids_is_not_throttled(self):
        await self._emit(self._status(song_id="id1"), now=100.0)

        await self._emit(self._status(song_id="id2"), now=100.1)

        self.message_handler.send_progress.assert_awaited_once()
        self.message_handler.edit_progress.assert_awaited_once()
        self.assertEqual(self.progress.song_key, "id2")

    async def test_id_is_used_as_key_for_followup_events(self):
        await self._emit(self._status(song_id="id1"), now=100.0)
        sent = self.progress.message

        await self._emit(self._status("finished", song_id="id1"), now=100.1)

        self.message_handler.send_progress.assert_awaited_once()
        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 4 * MB, 4 * MB)
        )

    async def test_call_scheduling_error_logs_warning_and_does_not_raise(self):
        def fail(coro, loop):
            coro.close()  # avoid a "never awaited" warning
            raise RuntimeError("Event loop is closed")

        self.mock_run_threadsafe.side_effect = fail

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            self.progress(self._status())

        self.assertEqual(len(logs.records), 1)
        self.assertIsNotNone(logs.records[0].exc_info)
        self.message_handler.send_progress.assert_not_called()

    async def test_call_malformed_status_logs_warning_and_does_not_raise(self):
        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            self.progress({})

        self.assertEqual(len(logs.records), 1)
        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertEqual(self.futures, [])

    async def test_call_from_worker_thread_with_error_does_not_raise(self):
        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self._emit({"status": "downloading"})

        self.assertEqual(len(logs.records), 1)
        self.message_handler.send_progress.assert_not_called()

    async def test_update_send_runtime_error_logs_warning(self):
        self.message_handler.send_progress.side_effect = RuntimeError("boom")

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("text")

        self.assertEqual(len(logs.records), 1)
        self.assertIsNone(self.progress.message)

    async def test_update_edit_runtime_error_logs_warning(self):
        sent = MagicMock(spec=discord.Message)
        self.progress.message = sent
        self.message_handler.edit_progress.side_effect = RuntimeError("boom")

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("text")

        self.assertEqual(len(logs.records), 1)
        self.message_handler.edit_progress.assert_awaited_once_with(sent, "text")
        self.assertIs(self.progress.message, sent)

    async def test_update_send_http_exception_logs_warning(self):
        self.message_handler.send_progress.side_effect = discord.HTTPException(
            MagicMock(status=500), "boom"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("text")

        self.assertEqual(len(logs.records), 1)
        self.assertIsNone(self.progress.message)

    async def test_update_edit_http_exception_logs_warning_and_resets_message(self):
        sent = MagicMock(spec=discord.Message)
        self.progress.message = sent
        self.message_handler.edit_progress.side_effect = discord.HTTPException(
            MagicMock(status=401), "Invalid Webhook Token"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("text")

        self.assertEqual(len(logs.records), 1)
        self.message_handler.edit_progress.assert_awaited_once_with(sent, "text")
        self.assertIsNone(self.progress.message)

    async def test_update_after_failed_edit_sends_new_message(self):
        self.progress.message = MagicMock(spec=discord.Message)
        self.message_handler.edit_progress.side_effect = discord.HTTPException(
            MagicMock(status=401), "Invalid Webhook Token"
        )
        with self.assertLogs("MusicBot", level=logging.WARNING):
            await self.progress._update("first")

        await self.progress._update("second")

        self.message_handler.send_progress.assert_awaited_once_with(self.ctx, "second")
        self.assertIsNotNone(self.progress.message)

    def _playlist_status(self, **info: Any) -> dict[str, Any]:
        status = self._status()
        status["info_dict"].update(info)
        return status

    async def test_playlist_index_with_n_entries_shows_counter(self):
        await self._emit(self._playlist_status(playlist_index=2, n_entries=20))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song (2/20)", MB, 4 * MB)
        )

    async def test_playlist_index_with_playlist_count_shows_counter(self):
        await self._emit(self._playlist_status(playlist_index=3, playlist_count=7))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song (3/7)", MB, 4 * MB)
        )

    async def test_playlist_n_entries_takes_precedence_over_playlist_count(self):
        await self._emit(
            self._playlist_status(playlist_index=1, n_entries=5, playlist_count=9)
        )

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song (1/5)", MB, 4 * MB)
        )

    async def test_playlist_without_index_shows_no_counter(self):
        await self._emit(self._playlist_status(n_entries=20))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song", MB, 4 * MB)
        )

    async def test_playlist_index_without_count_shows_no_counter(self):
        await self._emit(self._playlist_status(playlist_index=2))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song", MB, 4 * MB)
        )

    async def test_single_search_result_shows_no_counter(self):
        await self._emit(self._playlist_status(playlist_index=1, n_entries=1))

        self.message_handler.send_progress.assert_awaited_once_with(
            self.ctx, self._text("Song", MB, 4 * MB)
        )

    async def test_finish_without_message_returns_false_and_does_not_edit(self):
        result = await self.progress.finish("done", success=True)

        self.assertFalse(result)
        self.assertTrue(self.progress.done)
        self.message_handler.edit_success.assert_not_called()
        self.message_handler.edit_error.assert_not_called()
        self.ctx.send.assert_not_called()

    async def test_finish_success_edits_message_with_success(self):
        await self._emit(self._status())
        sent = self.progress.message

        result = await self.progress.finish("Added", success=True)

        self.assertTrue(result)
        self.message_handler.edit_success.assert_awaited_once_with(sent, "Added")
        self.message_handler.edit_error.assert_not_called()

    async def test_finish_failure_edits_message_with_error(self):
        await self._emit(self._status())
        sent = self.progress.message

        result = await self.progress.finish(
            CONST.MESSAGE_FAILED_VIDEO_INFO, success=False
        )

        self.assertTrue(result)
        self.message_handler.edit_error.assert_awaited_once_with(
            sent, CONST.MESSAGE_FAILED_VIDEO_INFO
        )
        self.message_handler.edit_success.assert_not_called()

    async def test_finish_http_exception_logs_warning_and_returns_false(self):
        self.progress.message = MagicMock(spec=discord.Message)
        self.message_handler.edit_success.side_effect = discord.HTTPException(
            MagicMock(status=500), "boom"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            result = await self.progress.finish("Added", success=True)

        self.assertFalse(result)
        self.assertEqual(len(logs.records), 1)
        self.assertIsNotNone(logs.records[0].exc_info)
        self.assertTrue(self.progress.done)

    async def test_update_after_finish_without_message_sends_nothing(self):
        await self.progress.finish("done", success=True)

        await self.progress._update("text")

        self.message_handler.send_progress.assert_not_called()
        self.assertIsNone(self.progress.message)

    async def test_update_after_finish_does_not_edit_final_message(self):
        await self._emit(self._status())
        await self.progress.finish("Added", success=True)

        await self._emit(
            self._status(downloaded=2 * MB),
            now=100.0 + CONST.PROGRESS_UPDATE_INTERVAL,
        )

        self.message_handler.send_progress.assert_awaited_once()
        self.message_handler.edit_progress.assert_not_called()

    async def test_update_scheduled_before_finish_running_after_is_ignored(self):
        await self._emit(self._status())
        sent = self.progress.message

        # Schedule an update without yielding, so it can only run after finish
        self.progress(self._status("finished", downloaded=4 * MB))
        self.assertEqual(len(self.futures), 2)
        self.assertFalse(self.futures[1].done())
        await self.progress.finish("Added", success=True)
        await asyncio.wrap_future(self.futures[1])

        self.message_handler.edit_success.assert_awaited_once_with(sent, "Added")
        self.message_handler.edit_progress.assert_not_called()
        self.message_handler.send_progress.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
