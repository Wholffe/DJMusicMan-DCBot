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
        sent = self.progress.messages["Song"]

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
        sent = self.progress.messages["Song"]

        await self._emit(self._status("finished", downloaded=4 * MB), now=100.1)

        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 4 * MB, 4 * MB)
        )
        self.assertIn("100%", self.message_handler.edit_progress.call_args[0][1])

    async def test_finished_without_downloaded_bytes_shows_complete(self):
        await self._emit(self._status(), now=100.0)
        sent = self.progress.messages["Song"]

        await self._emit(self._status("finished", downloaded=None), now=100.1)

        self.message_handler.edit_progress.assert_awaited_once_with(
            sent, self._text("Song", 4 * MB, 4 * MB)
        )

    async def test_finished_without_total_uses_downloaded_bytes(self):
        await self._emit(self._status(total=None), now=100.0)
        sent = self.progress.messages["Song"]

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
        self.assertEqual(self.progress.last_updates, {})

    async def test_new_title_sends_new_message(self):
        await self._emit(self._status(title="First"), now=100.0)

        await self._emit(self._status(title="Second"), now=100.1)

        self.assertEqual(
            [c.args[1] for c in self.message_handler.send_progress.await_args_list],
            [self._text("First", MB, 4 * MB), self._text("Second", MB, 4 * MB)],
        )
        self.message_handler.edit_progress.assert_not_called()
        self.assertEqual(set(self.progress.messages), {"First", "Second"})

    async def test_new_title_right_after_finished_is_sent(self):
        await self._emit(self._status(title="First"), now=100.0)
        await self._emit(self._status("finished", title="First"), now=100.0)

        await self._emit(self._status(title="Second"), now=100.0)

        self.assertEqual(self.message_handler.send_progress.await_count, 2)
        self.assertEqual(
            self.message_handler.send_progress.call_args[0][1],
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
        self.assertEqual(self.progress.last_updates, {})

    async def test_same_title_with_different_ids_sends_two_messages(self):
        await self._emit(self._status(song_id="id1"), now=100.0)

        await self._emit(self._status(song_id="id2"), now=100.1)

        self.assertEqual(self.message_handler.send_progress.await_count, 2)
        self.message_handler.edit_progress.assert_not_called()
        self.assertEqual(set(self.progress.messages), {"id1", "id2"})

    async def test_id_is_used_as_key_for_followup_events(self):
        await self._emit(self._status(song_id="id1"), now=100.0)
        sent = self.progress.messages["id1"]

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
            await self.progress._update("Song", "text")

        self.assertEqual(len(logs.records), 1)
        self.assertIn("Song", logs.output[0])
        self.assertNotIn("Song", self.progress.messages)

    async def test_update_edit_runtime_error_logs_warning(self):
        sent = MagicMock(spec=discord.Message)
        self.progress.messages["Song"] = sent
        self.message_handler.edit_progress.side_effect = RuntimeError("boom")

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("Song", "text")

        self.assertEqual(len(logs.records), 1)
        self.message_handler.edit_progress.assert_awaited_once_with(sent, "text")
        self.assertIs(self.progress.messages["Song"], sent)

    async def test_update_send_http_exception_logs_warning(self):
        self.message_handler.send_progress.side_effect = discord.HTTPException(
            MagicMock(status=500), "boom"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("Song", "text")

        self.assertEqual(len(logs.records), 1)
        self.assertIn("Song", logs.output[0])
        self.assertNotIn("Song", self.progress.messages)

    async def test_update_edit_http_exception_logs_warning(self):
        sent = MagicMock(spec=discord.Message)
        self.progress.messages["Song"] = sent
        self.message_handler.edit_progress.side_effect = discord.HTTPException(
            MagicMock(status=500), "boom"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            await self.progress._update("Song", "text")

        self.assertEqual(len(logs.records), 1)
        self.message_handler.edit_progress.assert_awaited_once_with(sent, "text")
        self.assertIs(self.progress.messages["Song"], sent)


if __name__ == "__main__":
    unittest.main()
