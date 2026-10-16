import json
import logging
import os
import tempfile
import threading
import unittest
from collections.abc import Callable
from functools import partial
from typing import Any
from unittest.mock import MagicMock, call, patch

from yt_dlp.utils import (  # type: ignore[import-untyped]
    DownloadError,
    ExtractorError,
)

from music_bot import cache_manager
from music_bot.cache_manager import CacheManager, _create_ydl
from music_bot.config import YDLP_OPTIONS

# Upper bound for joining download threads, so a deadlock fails instead of hanging
THREAD_TIMEOUT = 5.0
# How long the first fake download waits for a second one to start alongside it
OVERLAP_WAIT = 0.3


class BlockingDownload:
    """Fake yt-dlp download that holds the first call to detect overlapping calls."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.calls = 0
        self.other_started = threading.Event()
        self.overlapped = False

    def __call__(self, entry: Any, **kwargs: Any) -> Any:
        with self.lock:
            self.calls += 1
            is_first = self.calls == 1
        if not is_first:
            self.other_started.set()
            return entry
        # An unblocked second download starts within this wait. A blocked one
        # cannot, so the wait runs out and the result does not depend on timing.
        self.overlapped = self.other_started.wait(OVERLAP_WAIT)
        return entry


class TestCacheManager(unittest.TestCase):
    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        self.cache_dir = os.path.join(tmp_dir.name, "cache")

        cache_dir_patcher = patch("music_bot.cache_manager.CACHE_DIR", self.cache_dir)
        cache_dir_patcher.start()
        self.addCleanup(cache_dir_patcher.stop)

        # Keep a real data/cookies.txt from changing the yt-dlp options
        self.cookies_path = os.path.join(tmp_dir.name, "cookies.txt")
        cookies_patcher = patch(
            "music_bot.cache_manager.COOKIES_FILE_PATH", self.cookies_path
        )
        cookies_patcher.start()
        self.addCleanup(cookies_patcher.stop)

        ydl_patcher = patch("music_bot.cache_manager.yt_dlp.YoutubeDL")
        self.mock_ydl_cls = ydl_patcher.start()
        self.addCleanup(ydl_patcher.stop)
        self.ydl = MagicMock()
        self.mock_ydl_cls.return_value.__enter__.return_value = self.ydl
        self.ydl.prepare_filename.side_effect = self._song_path
        # Resolving an entry returns the full info, with keys that get pruned
        self.ydl.process_ie_result.side_effect = lambda entry, download, extra_info: {
            **entry,
            "duration": 1,
        }

        # cache_manager calls time.sleep through the module, so this skips the real
        # pause before a retry, also in the download threads
        sleep_patcher = patch("time.sleep")
        self.sleep = sleep_patcher.start()
        self.addCleanup(sleep_patcher.stop)

        logger = logging.getLogger("MusicBot")
        self.addCleanup(logger.setLevel, logger.level)
        logger.setLevel(logging.CRITICAL + 1)

        self.metadata_path = os.path.join(self.cache_dir, "metadata_cache.json")

    def _song_path(self, entry: dict) -> str:
        return os.path.join(self.cache_dir, f"{entry['id']}.webm")

    def _write_song_file(self, song_id: str, size: int = 0) -> str:
        path = os.path.join(self.cache_dir, f"{song_id}.webm")
        with open(path, "wb") as f:
            f.write(b"\0" * size)
        return path

    def _write_metadata(self, metadata: dict) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f)

    def _read_metadata(self) -> dict:
        with open(self.metadata_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _entry(song_id: str) -> dict:
        return {
            "id": song_id,
            "title": f"title {song_id}",
            "ext": "webm",
            "webpage_url": f"https://www.youtube.com/watch?v={song_id}",
        }

    def test_init_without_metadata_file_creates_dir_and_empty_cache(self):
        manager = CacheManager()

        self.assertTrue(os.path.isdir(self.cache_dir))
        self.assertEqual(manager.metadata_cache, {})

    def test_init_loads_existing_metadata(self):
        metadata = {"search": self._entry("a")}
        self._write_metadata(metadata)

        manager = CacheManager()

        self.assertEqual(manager.metadata_cache, metadata)

    def test_init_with_corrupt_metadata_returns_empty_cache(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.metadata_path, "w", encoding="utf-8") as f:
            f.write("{not json")

        manager = CacheManager()

        self.assertEqual(manager.metadata_cache, {})

    def test_prune_metadata_single_entry_keeps_essential_keys(self):
        manager = CacheManager()
        full_info = {**self._entry("a"), "duration": 120, "formats": [1, 2]}

        self.assertEqual(manager._prune_metadata(full_info), self._entry("a"))

    def test_prune_metadata_missing_keys_become_none(self):
        manager = CacheManager()

        pruned = manager._prune_metadata({"id": "a"})

        self.assertEqual(
            pruned, {"id": "a", "title": None, "ext": None, "webpage_url": None}
        )

    def test_prune_metadata_playlist_prunes_entries(self):
        manager = CacheManager()
        full_info = {
            "title": "playlist",
            "entries": [{**self._entry("a"), "x": 1}, {**self._entry("b"), "y": 2}],
        }

        pruned = manager._prune_metadata(full_info)

        self.assertEqual(pruned, {"entries": [self._entry("a"), self._entry("b")]})

    def _extra_info(self, index: int, count: int) -> dict:
        return {"playlist_index": index, "n_entries": count}

    def _assert_log_line(self, record: logging.LogRecord, *texts: str) -> None:
        """Asserts a single log line without traceback that contains the texts."""
        message = record.getMessage()
        self.assertIsNone(record.exc_info)
        self.assertNotIn("\n", message)
        for text in texts:
            self.assertIn(text, message)

    def test_iter_songs_cached_with_existing_file_does_not_download(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        path = self._write_song_file("a")

        songs = list(manager.iter_songs("search"))

        self.assertEqual(songs, [{"url": path, "title": "title a"}])
        self.ydl.extract_info.assert_not_called()
        self.ydl.process_ie_result.assert_not_called()

    def test_iter_songs_cached_with_missing_file_downloads_it(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()

        songs = list(manager.iter_songs("search"))

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.ydl.extract_info.assert_called_once_with(
            self._entry("a")["webpage_url"],
            download=True,
            extra_info=self._extra_info(1, 1),
        )

    def test_iter_songs_cached_playlist_passes_index_and_count(self):
        entries = [self._entry("a"), self._entry("b")]
        self._write_metadata({"playlist": {"entries": entries}})
        manager = CacheManager()

        list(manager.iter_songs("playlist"))

        self.assertEqual(
            [c.kwargs["extra_info"] for c in self.ydl.extract_info.call_args_list],
            [self._extra_info(1, 2), self._extra_info(2, 2)],
        )

    def test_iter_songs_new_search_fetches_and_caches_pruned_info(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")

        songs = list(manager.iter_songs("new search"))

        self.ydl.extract_info.assert_called_once_with(
            "new search", download=False, process=False
        )
        self.ydl.process_ie_result.assert_called_once_with(
            self._entry("a"), download=True, extra_info=self._extra_info(1, 1)
        )
        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        expected = {"entries": [self._entry("a")]}
        self.assertEqual(manager.metadata_cache, {"new search": expected})
        self.assertEqual(self._read_metadata(), {"new search": expected})

    def test_iter_songs_new_playlist_caches_entries(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {
            "entries": [self._entry("a"), None, self._entry("b")]
        }

        songs = list(manager.iter_songs("playlist"))

        self.assertEqual([song["title"] for song in songs], ["title a", "title b"])
        self.assertEqual(
            [c.kwargs["extra_info"] for c in self.ydl.process_ie_result.call_args_list],
            [self._extra_info(1, 2), self._extra_info(2, 2)],
        )
        expected = {"entries": [self._entry("a"), self._entry("b")]}
        self.assertEqual(manager.metadata_cache, {"playlist": expected})
        self.assertEqual(self._read_metadata(), {"playlist": expected})

    def test_iter_songs_new_playlist_yields_first_song_before_next_download(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {
            "entries": [self._entry("a"), self._entry("b")]
        }
        songs = manager.iter_songs("playlist")

        first = next(songs)

        self.assertEqual(first["title"], "title a")
        self.ydl.process_ie_result.assert_called_once()
        self.assertEqual(manager.metadata_cache, {})
        self.assertFalse(os.path.exists(self.metadata_path))

    def test_iter_songs_new_playlist_closed_early_caches_nothing(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {
            "entries": [self._entry("a"), self._entry("b")]
        }
        songs = manager.iter_songs("playlist")
        next(songs)

        songs.close()

        self.ydl.process_ie_result.assert_called_once()
        self.assertEqual(manager.metadata_cache, {})
        self.assertFalse(os.path.exists(self.metadata_path))

    def test_iter_songs_new_playlist_skips_failed_entry_and_caches_rest(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [
            {"entries": [self._entry("a"), self._entry("b"), self._entry("c")]},
            DownloadError("failed"),
        ]

        def process(entry: dict, download: bool, extra_info: dict) -> dict:
            if entry["id"] == "b":
                raise DownloadError("failed")
            return entry

        self.ydl.process_ie_result.side_effect = process

        songs = list(manager.iter_songs("playlist"))

        self.assertEqual([song["title"] for song in songs], ["title a", "title c"])
        self.assertEqual(
            manager.metadata_cache,
            {"playlist": {"entries": [self._entry("a"), self._entry("c")]}},
        )

    def test_iter_songs_new_playlist_flattens_nested_entries(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {"entries": [{"url": "nested"}]}
        self.ydl.process_ie_result.side_effect = None
        self.ydl.process_ie_result.return_value = {
            "entries": [self._entry("a"), self._entry("b")]
        }

        songs = list(manager.iter_songs("playlist"))

        self.assertEqual([song["title"] for song in songs], ["title a", "title b"])
        self.assertEqual(
            manager.metadata_cache,
            {"playlist": {"entries": [self._entry("a"), self._entry("b")]}},
        )

    def test_iter_songs_new_search_without_info_yields_nothing(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = None

        songs = list(manager.iter_songs("nothing"))

        self.assertEqual(songs, [])
        self.ydl.process_ie_result.assert_not_called()
        self.assertEqual(manager.metadata_cache, {})

    def test_iter_songs_new_search_all_downloads_failed_caches_nothing(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [self._entry("a"), ExtractorError("failed")]
        self.ydl.process_ie_result.side_effect = ExtractorError("failed")

        songs = list(manager.iter_songs("broken"))

        self.assertEqual(songs, [])
        self.assertEqual(manager.metadata_cache, {})
        self.assertFalse(os.path.exists(self.metadata_path))

    def test_iter_songs_new_search_retries_failed_download_once(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")
        # YouTube sporadically answers with HTTP 403, a second attempt usually works
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        songs = list(manager.iter_songs("new search"))

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.ydl.process_ie_result.assert_called_once_with(
            self._entry("a"), download=True, extra_info=self._extra_info(1, 1)
        )
        self.assertEqual(
            self.ydl.extract_info.call_args_list[1:],
            [
                call(
                    self._entry("a")["webpage_url"],
                    download=True,
                    extra_info=self._extra_info(1, 1),
                )
            ],
        )
        self.assertEqual(
            manager.metadata_cache, {"new search": {"entries": [self._entry("a")]}}
        )

    def test_iter_songs_new_search_download_failing_all_attempts_gives_up(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [
            self._entry("a"),
            *[DownloadError("failed")] * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        ]
        self.ydl.process_ie_result.side_effect = DownloadError("failed")

        songs = list(manager.iter_songs("broken"))

        self.assertEqual(songs, [])
        # The first attempt runs in the instance of the search, each retry in a new one
        self.assertEqual(self.mock_ydl_cls.call_count, cache_manager.DOWNLOAD_ATTEMPTS)
        self.assertEqual(manager.metadata_cache, {})

    def test_iter_songs_new_search_failed_download_pauses_before_retry(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")
        # An immediate retry often got HTTP 403 again, so it waits first
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        songs = list(manager.iter_songs("new search"))

        self.assertEqual([song["title"] for song in songs], ["title a"])
        self.assertEqual(
            self.sleep.call_args_list, [call(cache_manager.DOWNLOAD_RETRY_DELAY)]
        )

    def test_iter_songs_new_search_failing_download_pauses_between_attempts(self):
        manager = CacheManager()
        events: list[str] = []

        def fail_download(*args: Any, **kwargs: Any) -> None:
            events.append("download")
            raise DownloadError("HTTP Error 403: Forbidden")

        def extract_info(search: str, download: bool, **kwargs: Any) -> Any:
            # The search only extracts here, the retries download
            return fail_download() if download else self._entry("a")

        self.ydl.extract_info.side_effect = extract_info
        self.ydl.process_ie_result.side_effect = fail_download
        self.sleep.side_effect = lambda seconds: events.append("sleep")

        list(manager.iter_songs("broken"))

        # No pause before the first attempt and none after the last one
        self.assertEqual(
            events,
            ["download"]
            + ["sleep", "download"] * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        )
        self.assertEqual(
            self.sleep.call_args_list,
            [call(cache_manager.DOWNLOAD_RETRY_DELAY)]
            * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        )

    def test_iter_songs_new_search_successful_download_does_not_pause(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")

        list(manager.iter_songs("new search"))

        self.sleep.assert_not_called()

    def test_iter_songs_new_search_failed_download_logs_one_line_with_reason(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        self.ydl.extract_info.side_effect = [
            self._entry("a"),
            *[DownloadError("HTTP Error 403: Forbidden")]
            * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        ]
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            list(manager.iter_songs("new search"))

        self.assertEqual(len(logs.records), 1)
        self._assert_log_line(logs.records[0], url, "HTTP Error 403: Forbidden")

    def test_iter_songs_new_search_retry_logs_info_line_with_reason(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        self.ydl.extract_info.return_value = self._entry("a")
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        with self.assertLogs("MusicBot", level=logging.INFO) as logs:
            list(manager.iter_songs("new search"))

        # A retry that works logs no warning
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].levelno, logging.INFO)
        self._assert_log_line(logs.records[0], url, "HTTP Error 403: Forbidden")

    def test_iter_songs_new_playlist_retries_only_failed_entry(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [
            {"entries": [self._entry("a"), self._entry("b")]},
            self._entry("b"),
        ]
        self.ydl.process_ie_result.side_effect = [
            self._entry("a"),
            DownloadError("HTTP Error 403: Forbidden"),
        ]

        songs = list(manager.iter_songs("playlist"))

        self.assertEqual([song["title"] for song in songs], ["title a", "title b"])
        self.assertEqual(
            [c.kwargs["extra_info"] for c in self.ydl.process_ie_result.call_args_list],
            [self._extra_info(1, 2), self._extra_info(2, 2)],
        )
        self.assertEqual(
            self.ydl.extract_info.call_args_list[1],
            call(
                self._entry("b")["webpage_url"],
                download=True,
                extra_info=self._extra_info(2, 2),
            ),
        )

    def test_iter_songs_new_video_retry_extracts_video_again(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        stale = {**self._entry("a"), "formats": ["rejected link"]}
        fresh = {**self._entry("a"), "formats": ["fresh link"]}
        self.ydl.extract_info.side_effect = [stale, fresh]
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        songs = list(manager.iter_songs(url))

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.assertEqual(
            self.ydl.extract_info.call_args_list,
            [
                call(url, download=False, process=False),
                call(url, download=True, extra_info=self._extra_info(1, 1)),
            ],
        )
        self.ydl.process_ie_result.assert_called_once_with(
            stale, download=True, extra_info=self._extra_info(1, 1)
        )

    def test_iter_songs_new_playlist_retry_extracts_flat_entry_again(self):
        manager = CacheManager()
        # Playlist entries are flat entries that only point to the video
        flat_entry = {
            "_type": "url",
            "url": "https://www.youtube.com/watch?v=a",
            "id": "a",
        }
        self.ydl.extract_info.side_effect = [
            {"entries": [flat_entry]},
            self._entry("a"),
        ]
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        songs = list(manager.iter_songs("playlist"))

        self.assertEqual([song["title"] for song in songs], ["title a"])
        self.assertEqual(
            self.ydl.extract_info.call_args_list[1],
            call(flat_entry["url"], download=True, extra_info=self._extra_info(1, 1)),
        )

    def test_iter_songs_new_search_retry_extracts_search_again(self):
        manager = CacheManager()
        # yt-dlp turns a search into a flat entry that points to the search results
        self.ydl.extract_info.side_effect = [
            {
                "_type": "url",
                "url": "ytsearch:new search",
                "webpage_url": "new search",
            },
            {"entries": [self._entry("a")]},
        ]
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )

        songs = list(manager.iter_songs("new search"))

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.assertEqual(
            self.ydl.extract_info.call_args_list,
            [
                call("new search", download=False, process=False),
                call("new search", download=True, extra_info=self._extra_info(1, 1)),
            ],
        )

    def test_iter_songs_new_search_failed_extraction_on_retry_skips_song(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [
            self._entry("a"),
            ExtractorError("HTTP Error 403: Forbidden"),
        ]
        self.ydl.process_ie_result.side_effect = DownloadError("failed")

        songs = list(manager.iter_songs("broken"))

        self.assertEqual(songs, [])
        self.ydl.process_ie_result.assert_called_once()
        self.assertEqual(manager.metadata_cache, {})

    def test_iter_songs_new_search_retry_downloads_in_new_ydl_instance(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        hook = MagicMock()
        self.ydl.extract_info.return_value = self._entry("a")
        self.ydl.process_ie_result.side_effect = DownloadError(
            "HTTP Error 403: Forbidden"
        )
        retry_ydl = MagicMock()
        retry_ydl.extract_info.return_value = self._entry("a")
        retry_instance = MagicMock()
        retry_instance.__enter__.return_value = retry_ydl
        self.mock_ydl_cls.side_effect = [self.mock_ydl_cls.return_value, retry_instance]

        songs = list(manager.iter_songs("new search", progress_hook=hook))

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        # The first attempt runs in the instance of the search
        self.ydl.process_ie_result.assert_called_once()
        retry_ydl.extract_info.assert_called_once_with(
            url, download=True, extra_info=self._extra_info(1, 1)
        )
        retry_params = self._ydl_params()[1]
        self.assertEqual(retry_params["progress_hooks"], [hook])
        self.assertFalse(retry_params["skip_download"])

    def _ydl_params(self) -> list[dict]:
        return [c.args[0] for c in self.mock_ydl_cls.call_args_list]

    def test_create_ydl_without_hook_has_no_progress_hooks(self):
        _create_ydl(download=True)

        params = self.mock_ydl_cls.call_args[0][0]
        self.assertNotIn("progress_hooks", params)
        self.assertFalse(params["skip_download"])

    def test_create_ydl_with_hook_sets_progress_hooks(self):
        hook = MagicMock()

        _create_ydl(download=True, progress_hook=hook)

        params = self.mock_ydl_cls.call_args[0][0]
        self.assertEqual(params["progress_hooks"], [hook])
        self.assertFalse(params["skip_download"])
        self.assertNotIn("progress_hooks", YDLP_OPTIONS)

    def test_create_ydl_info_only_with_hook_keeps_options(self):
        hook = MagicMock()

        _create_ydl(progress_hook=hook)

        params = self.mock_ydl_cls.call_args[0][0]
        self.assertEqual(params, {**YDLP_OPTIONS, "progress_hooks": [hook]})
        self.assertNotIn("progress_hooks", YDLP_OPTIONS)

    def test_iter_songs_new_search_passes_progress_hook(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")
        hook = MagicMock()

        list(manager.iter_songs("new search", progress_hook=hook))

        download_params = [p for p in self._ydl_params() if "skip_download" in p]
        self.assertEqual(len(download_params), 1)
        self.assertEqual(download_params[0]["progress_hooks"], [hook])

    def test_iter_songs_cached_with_missing_file_passes_progress_hook(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        hook = MagicMock()

        list(manager.iter_songs("search", progress_hook=hook))

        download_params = [p for p in self._ydl_params() if "skip_download" in p]
        self.assertEqual(len(download_params), 1)
        self.assertEqual(download_params[0]["progress_hooks"], [hook])

    def test_iter_songs_without_hook_sets_no_progress_hooks(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()

        list(manager.iter_songs("search"))

        for params in self._ydl_params():
            self.assertNotIn("progress_hooks", params)

    def test_iter_songs_download_error_yields_nothing_and_does_not_cache(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("failed")

        songs = list(manager.iter_songs("broken"))

        self.assertEqual(songs, [])
        self.ydl.process_ie_result.assert_not_called()
        self.assertEqual(manager.metadata_cache, {})

    def test_iter_songs_fetch_error_logs_one_line_with_reason(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("HTTP Error 403: Forbidden")

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            list(manager.iter_songs("broken search"))

        self.assertEqual(len(logs.records), 1)
        self._assert_log_line(
            logs.records[0], "broken search", "HTTP Error 403: Forbidden"
        )

    def test_iter_cached_entries_skips_empty_and_defaults_title(self):
        manager = CacheManager()
        entry = {"id": "a", "webpage_url": "https://www.youtube.com/watch?v=a"}
        self._write_song_file("a")

        songs = list(manager._iter_cached_entries([None, {}, entry]))  # type: ignore[list-item]

        self.assertEqual(
            songs, [{"url": self._song_path(entry), "title": "Unknown Title"}]
        )

    def test_ydlp_options_have_no_cookiefile(self):
        self.assertNotIn("cookiefile", YDLP_OPTIONS)

    def test_create_ydl_without_cookie_file_has_no_cookiefile(self):
        _create_ydl()

        params = self.mock_ydl_cls.call_args[0][0]
        self.assertNotIn("cookiefile", params)
        self.assertFalse(os.path.exists(self.cookies_path))

    def test_create_ydl_with_cookie_file_sets_cookiefile(self):
        with open(self.cookies_path, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")

        _create_ydl(download=True)

        params = self.mock_ydl_cls.call_args[0][0]
        self.assertEqual(params["cookiefile"], self.cookies_path)
        self.assertNotIn("cookiefile", YDLP_OPTIONS)

    def test_create_ydl_cookie_path_is_directory_has_no_cookiefile(self):
        os.makedirs(self.cookies_path)

        _create_ydl()

        self.assertNotIn("cookiefile", self.mock_ydl_cls.call_args[0][0])

    def test_download_song_if_missing_download_error_returns_none(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("failed")

        self.assertIsNone(manager._download_song_if_missing(self._entry("a")))

    def test_download_song_if_missing_extractor_error_returns_none(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = ExtractorError("failed")

        self.assertIsNone(manager._download_song_if_missing(self._entry("a")))

    def test_download_song_if_missing_retries_failed_download_once(self):
        manager = CacheManager()
        # YouTube sporadically answers with HTTP 403, a second attempt usually works
        self.ydl.extract_info.side_effect = [
            DownloadError("HTTP Error 403: Forbidden"),
            None,
        ]

        filepath = manager._download_song_if_missing(self._entry("a"))

        self.assertEqual(filepath, self._song_path(self._entry("a")))
        self.assertEqual(
            self.ydl.extract_info.call_args_list,
            [call(self._entry("a")["webpage_url"], download=True, extra_info=None)] * 2,
        )

    def test_download_song_if_missing_failing_all_attempts_returns_none(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("failed")

        self.assertIsNone(manager._download_song_if_missing(self._entry("a")))
        self.assertEqual(
            self.ydl.extract_info.call_count, cache_manager.DOWNLOAD_ATTEMPTS
        )

    def test_download_song_if_missing_failed_download_pauses_before_retry(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [
            DownloadError("HTTP Error 403: Forbidden"),
            None,
        ]

        filepath = manager._download_song_if_missing(self._entry("a"))

        self.assertEqual(filepath, self._song_path(self._entry("a")))
        self.assertEqual(
            self.sleep.call_args_list, [call(cache_manager.DOWNLOAD_RETRY_DELAY)]
        )

    def test_download_song_if_missing_failing_pauses_between_attempts(self):
        manager = CacheManager()
        events: list[str] = []

        def fail_download(url: str, download: bool, extra_info: dict) -> None:
            events.append("download")
            raise DownloadError("HTTP Error 403: Forbidden")

        self.ydl.extract_info.side_effect = fail_download
        self.sleep.side_effect = lambda seconds: events.append("sleep")

        manager._download_song_if_missing(self._entry("a"))

        # No pause before the first attempt and none after the last one
        self.assertEqual(
            events,
            ["download"]
            + ["sleep", "download"] * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        )
        self.assertEqual(
            self.sleep.call_args_list,
            [call(cache_manager.DOWNLOAD_RETRY_DELAY)]
            * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
        )

    def test_download_song_if_missing_successful_download_does_not_pause(self):
        manager = CacheManager()

        manager._download_song_if_missing(self._entry("a"))

        self.sleep.assert_not_called()

    def test_download_song_if_missing_failed_download_logs_one_line_with_reason(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        self.ydl.extract_info.side_effect = DownloadError("HTTP Error 403: Forbidden")

        with self.assertLogs("MusicBot", level=logging.WARNING) as logs:
            manager._download_song_if_missing(self._entry("a"))

        self.assertEqual(len(logs.records), 1)
        self._assert_log_line(logs.records[0], url, "HTTP Error 403: Forbidden")

    def test_download_song_if_missing_retry_logs_info_line_with_reason(self):
        manager = CacheManager()
        url = self._entry("a")["webpage_url"]
        self.ydl.extract_info.side_effect = [
            DownloadError("HTTP Error 403: Forbidden"),
            None,
        ]

        with self.assertLogs("MusicBot", level=logging.INFO) as logs:
            manager._download_song_if_missing(self._entry("a"))

        # A retry that works logs no warning
        self.assertEqual(len(logs.records), 1)
        self.assertEqual(logs.records[0].levelno, logging.INFO)
        self._assert_log_line(logs.records[0], url, "HTTP Error 403: Forbidden")

    def _run_in_threads(self, *downloads: Callable[[], Any]) -> list[Any]:
        """Runs the downloads in parallel threads and returns their results."""
        results: list[Any] = [None] * len(downloads)

        def run(index: int, download: Callable[[], Any]) -> None:
            results[index] = download()

        # Daemon threads, so a deadlock fails the test instead of hanging the run
        threads = [
            threading.Thread(target=run, args=(index, download), daemon=True)
            for index, download in enumerate(downloads)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(THREAD_TIMEOUT)
            self.assertFalse(thread.is_alive())
        return results

    @staticmethod
    def _search_entry(search: str) -> dict:
        # Search results have no id until yt-dlp resolves them
        return {"_type": "url", "url": f"ytsearch:{search}"}

    def _song(self, song_id: str) -> dict:
        path = self._song_path(self._entry(song_id))
        return {"url": path, "title": f"title {song_id}"}

    def _new_songs(self, manager: CacheManager, search: str) -> Callable[[], Any]:
        """Returns a call that fetches all songs of a new search."""
        return partial(list, manager._fetch_and_cache_new_songs(search))

    def _cached_songs(self, manager: CacheManager, song_id: str) -> Callable[[], Any]:
        """Returns a call that gets the song of a cached entry."""
        return partial(list, manager._iter_cached_entries([self._entry(song_id)]))

    def test_fetch_and_cache_new_songs_same_video_waits_for_running_download(self):
        manager = CacheManager()
        downloads = BlockingDownload()
        self.ydl.process_ie_result.side_effect = downloads
        self.ydl.extract_info.return_value = self._entry("a")

        results = self._run_in_threads(
            self._new_songs(manager, "a"), self._new_songs(manager, "a")
        )

        self.assertFalse(downloads.overlapped)
        self.assertEqual(results, [[self._song("a")], [self._song("a")]])

    def test_fetch_and_cache_new_songs_same_search_waits_for_running_download(self):
        manager = CacheManager()
        downloads = BlockingDownload()
        self.ydl.extract_info.side_effect = [
            self._search_entry("song"),
            self._search_entry("song"),
        ]
        # A search resolves to a playlist with the found video
        self.ydl.process_ie_result.side_effect = lambda entry, **kwargs: {
            "entries": [downloads(self._entry("a"))]
        }

        results = self._run_in_threads(
            self._new_songs(manager, "song"), self._new_songs(manager, "song")
        )

        self.assertFalse(downloads.overlapped)
        self.assertEqual(results, [[self._song("a")], [self._song("a")]])

    def test_iter_cached_entries_waits_for_new_download_of_same_video(self):
        manager = CacheManager()
        downloads = BlockingDownload()
        self.ydl.process_ie_result.side_effect = downloads

        def extract_info(url: str, download: bool, **kwargs: Any) -> Any:
            # The new search only extracts here, the cached entry downloads
            return downloads(url) if download else self._entry("a")

        self.ydl.extract_info.side_effect = extract_info

        results = self._run_in_threads(
            self._new_songs(manager, "a"), self._cached_songs(manager, "a")
        )

        self.assertFalse(downloads.overlapped)
        self.assertEqual(results, [[self._song("a")], [self._song("a")]])

    def test_iter_cached_entries_waiting_call_uses_finished_file(self):
        manager = CacheManager()
        downloads = BlockingDownload()

        def extract_info(url: str, **kwargs: Any) -> None:
            downloads(url)
            self._write_song_file("a")

        self.ydl.extract_info.side_effect = extract_info

        results = self._run_in_threads(
            self._cached_songs(manager, "a"), self._cached_songs(manager, "a")
        )

        self.assertFalse(downloads.overlapped)
        self.ydl.extract_info.assert_called_once()
        self.assertEqual(results, [[self._song("a")], [self._song("a")]])

    def test_fetch_and_cache_new_songs_different_videos_run_in_parallel(self):
        manager = CacheManager()
        downloads = BlockingDownload()
        self.ydl.process_ie_result.side_effect = downloads
        # The searches are the ids of the found videos
        self.ydl.extract_info.side_effect = lambda search, **kwargs: self._entry(search)

        results = self._run_in_threads(
            self._new_songs(manager, "a"), self._new_songs(manager, "b")
        )

        self.assertTrue(downloads.overlapped)
        self.assertEqual(results, [[self._song("a")], [self._song("b")]])

    def test_fetch_and_cache_new_songs_different_searches_run_in_parallel(self):
        manager = CacheManager()
        downloads = BlockingDownload()

        def extract_info(search: str, **kwargs: Any) -> dict:
            return self._search_entry(search)

        self.ydl.extract_info.side_effect = extract_info
        # A search resolves to a playlist with the found video
        found = {
            "ytsearch:first": self._entry("a"),
            "ytsearch:second": self._entry("b"),
        }
        self.ydl.process_ie_result.side_effect = lambda entry, **kwargs: {
            "entries": [downloads(found[entry["url"]])]
        }

        results = self._run_in_threads(
            self._new_songs(manager, "first"), self._new_songs(manager, "second")
        )

        self.assertTrue(downloads.overlapped)
        self.assertEqual(results, [[self._song("a")], [self._song("b")]])

    def test_fetch_and_cache_new_songs_failed_download_releases_video_lock(self):
        manager = CacheManager()
        # The first fetch fails in every attempt, the second one works
        self.ydl.extract_info.side_effect = [
            self._entry("a"),
            *[DownloadError("failed")] * (cache_manager.DOWNLOAD_ATTEMPTS - 1),
            self._entry("a"),
        ]
        self.ydl.process_ie_result.side_effect = [
            DownloadError("failed"),
            self._entry("a"),
        ]
        list(manager._fetch_and_cache_new_songs("a"))

        results = self._run_in_threads(self._new_songs(manager, "a"))

        self.assertEqual(results, [[self._song("a")]])

    def test_iter_cached_entries_unexpected_error_releases_video_lock(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = [RuntimeError("boom"), None]
        with self.assertRaises(RuntimeError):
            list(manager._iter_cached_entries([self._entry("a")]))

        results = self._run_in_threads(self._cached_songs(manager, "a"))

        self.assertEqual(results, [[self._song("a")]])

    def test_fetch_and_cache_new_songs_releases_video_lock_before_yield(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")
        songs = manager._fetch_and_cache_new_songs("a")
        next(songs)

        # Times out if the paused generator still holds the lock of the video
        results = self._run_in_threads(self._cached_songs(manager, "a"))

        self.assertEqual(results, [[self._song("a")]])

    def test_iter_cached_entries_releases_video_lock_before_yield(self):
        manager = CacheManager()
        songs = manager._iter_cached_entries([self._entry("a")])
        next(songs)

        # Times out if the paused generator still holds the lock of the video
        results = self._run_in_threads(self._cached_songs(manager, "a"))

        self.assertEqual(results, [[self._song("a")]])

    def test_iter_cached_entries_skips_entry_with_failed_download(self):
        manager = CacheManager()
        self._write_song_file("b")
        failing_url = self._entry("a")["webpage_url"]

        def extract_info(url: str, download: bool, extra_info: dict) -> None:
            if url == failing_url:
                raise DownloadError("failed")

        self.ydl.extract_info.side_effect = extract_info

        songs = list(
            manager._iter_cached_entries(
                [self._entry("a"), self._entry("b"), self._entry("c")]
            )
        )

        self.assertEqual(
            songs,
            [
                {"url": self._song_path(self._entry("b")), "title": "title b"},
                {"url": self._song_path(self._entry("c")), "title": "title c"},
            ],
        )

    def test_iter_songs_cached_with_failing_download_yields_nothing(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("failed")

        self.assertEqual(list(manager.iter_songs("search")), [])
        self.assertEqual(manager.metadata_cache, {"search": self._entry("a")})

    def test_enforce_cache_limit_removes_oldest_entry_and_file(self):
        manager = CacheManager()
        old_path = self._write_song_file("old")
        new_path = self._write_song_file("new")
        manager.metadata_cache = {
            "old search": self._entry("old"),
            "new search": self._entry("new"),
        }

        with patch("music_bot.cache_manager.MAX_CACHE_FILES", 1):
            manager._enforce_cache_limit()

        self.assertEqual(list(manager.metadata_cache), ["new search"])
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(new_path))
        self.assertEqual(self._read_metadata(), {"new search": self._entry("new")})

    def test_iter_songs_cache_hit_keeps_entry_over_least_recently_used(self):
        self._write_metadata(
            {"a search": self._entry("a"), "b search": self._entry("b")}
        )
        manager = CacheManager()
        path_a = self._write_song_file("a")
        path_b = self._write_song_file("b")
        list(manager.iter_songs("a search"))
        self.ydl.extract_info.return_value = self._entry("c")

        with patch("music_bot.cache_manager.MAX_CACHE_FILES", 2):
            list(manager.iter_songs("c search"))

        self.assertEqual(list(manager.metadata_cache), ["a search", "c search"])
        self.assertTrue(os.path.exists(path_a))
        self.assertFalse(os.path.exists(path_b))

    def test_iter_songs_cache_hit_saves_new_order_to_metadata_file(self):
        self._write_metadata(
            {"a search": self._entry("a"), "b search": self._entry("b")}
        )
        manager = CacheManager()
        self._write_song_file("a")

        list(manager.iter_songs("a search"))

        self.assertEqual(list(self._read_metadata()), ["b search", "a search"])

    def test_enforce_cache_limit_removes_all_playlist_files(self):
        manager = CacheManager()
        paths = [self._write_song_file("a"), self._write_song_file("b")]
        manager.metadata_cache = {
            "playlist": {"entries": [self._entry("a"), self._entry("b")]},
            "single": self._entry("c"),
        }

        with patch("music_bot.cache_manager.MAX_CACHE_FILES", 1):
            manager._enforce_cache_limit()

        self.assertEqual(list(manager.metadata_cache), ["single"])
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def test_enforce_cache_limit_under_limit_keeps_entries(self):
        manager = CacheManager()
        manager.metadata_cache = {"search": self._entry("a")}

        with patch("music_bot.cache_manager.MAX_CACHE_FILES", 5):
            manager._enforce_cache_limit()

        self.assertEqual(manager.metadata_cache, {"search": self._entry("a")})
        self.assertEqual(self._read_metadata(), {"search": self._entry("a")})

    def test_clear_cache_deletes_files_and_returns_stats(self):
        manager = CacheManager()
        mb = 1024 * 1024
        path_a = self._write_song_file("a", size=mb)
        path_b = self._write_song_file("b", size=mb // 2)
        manager.metadata_cache = {
            "single": self._entry("a"),
            "playlist": {"entries": [self._entry("b"), self._entry("missing")]},
        }

        deleted_files, total_size_mb = manager.clear_cache()

        self.assertEqual((deleted_files, total_size_mb), (2, 1.5))
        self.assertFalse(os.path.exists(path_a))
        self.assertFalse(os.path.exists(path_b))
        self.assertEqual(manager.metadata_cache, {})
        self.assertEqual(self._read_metadata(), {})

    def test_clear_cache_empty_returns_zero(self):
        manager = CacheManager()

        self.assertEqual(manager.clear_cache(), (0, 0.0))


if __name__ == "__main__":
    unittest.main()
