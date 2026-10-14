import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from yt_dlp.utils import (  # type: ignore[import-untyped]
    DownloadError,
    ExtractorError,
)

from music_bot.cache_manager import CacheManager, _create_ydl
from music_bot.config import YDLP_OPTIONS


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

    def test_get_songs_cached_with_existing_file_does_not_download(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        path = self._write_song_file("a")

        songs = manager.get_songs("search")

        self.assertEqual(songs, [{"url": path, "title": "title a"}])
        self.ydl.extract_info.assert_not_called()
        self.ydl.download.assert_not_called()

    def test_get_songs_cached_with_missing_file_downloads_it(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()

        songs = manager.get_songs("search")

        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.ydl.download.assert_called_once_with([self._entry("a")["webpage_url"]])
        self.ydl.extract_info.assert_not_called()

    def test_get_songs_new_search_fetches_and_caches_pruned_info(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {**self._entry("a"), "duration": 1}
        self._write_song_file("a")

        songs = manager.get_songs("new search")

        self.ydl.extract_info.assert_called_once_with("new search", download=True)
        self.assertEqual(
            songs, [{"url": self._song_path(self._entry("a")), "title": "title a"}]
        )
        self.assertEqual(manager.metadata_cache, {"new search": self._entry("a")})
        self.assertEqual(self._read_metadata(), {"new search": self._entry("a")})

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

    def test_get_songs_new_search_passes_progress_hook(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = self._entry("a")
        self._write_song_file("a")
        hook = MagicMock()

        manager.get_songs("new search", progress_hook=hook)

        download_params = [p for p in self._ydl_params() if "skip_download" in p]
        self.assertEqual(len(download_params), 1)
        self.assertEqual(download_params[0]["progress_hooks"], [hook])

    def test_get_songs_cached_with_missing_file_passes_progress_hook(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        hook = MagicMock()

        manager.get_songs("search", progress_hook=hook)

        download_params = [p for p in self._ydl_params() if "skip_download" in p]
        self.assertEqual(len(download_params), 1)
        self.assertEqual(download_params[0]["progress_hooks"], [hook])
        self.ydl.download.assert_called_once_with([self._entry("a")["webpage_url"]])

    def test_get_songs_without_hook_sets_no_progress_hooks(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()

        manager.get_songs("search")

        for params in self._ydl_params():
            self.assertNotIn("progress_hooks", params)

    def test_get_songs_playlist_returns_all_entries(self):
        manager = CacheManager()
        self.ydl.extract_info.return_value = {
            "entries": [self._entry("a"), self._entry("b")]
        }
        self._write_song_file("a")
        self._write_song_file("b")

        songs = manager.get_songs("playlist")

        self.assertEqual([song["title"] for song in songs], ["title a", "title b"])

    def test_get_songs_download_error_returns_empty_and_does_not_cache(self):
        manager = CacheManager()
        self.ydl.extract_info.side_effect = DownloadError("failed")

        songs = manager.get_songs("broken")

        self.assertEqual(songs, [])
        self.assertEqual(manager.metadata_cache, {})

    def test_process_entries_skips_empty_and_defaults_title(self):
        manager = CacheManager()
        entry = {"id": "a", "webpage_url": "https://www.youtube.com/watch?v=a"}
        self._write_song_file("a")

        songs = manager._process_entries([None, {}, entry])  # type: ignore[list-item]

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
        self.ydl.download.side_effect = DownloadError("failed")

        self.assertIsNone(manager._download_song_if_missing(self._entry("a")))

    def test_download_song_if_missing_extractor_error_returns_none(self):
        manager = CacheManager()
        self.ydl.download.side_effect = ExtractorError("failed")

        self.assertIsNone(manager._download_song_if_missing(self._entry("a")))

    def test_process_entries_skips_entry_with_failed_download(self):
        manager = CacheManager()
        self._write_song_file("b")
        failing_url = self._entry("a")["webpage_url"]

        def download(urls: list[str]) -> None:
            if urls == [failing_url]:
                raise DownloadError("failed")

        self.ydl.download.side_effect = download

        songs = manager._process_entries(
            [self._entry("a"), self._entry("b"), self._entry("c")]
        )

        self.assertEqual(
            songs,
            [
                {"url": self._song_path(self._entry("b")), "title": "title b"},
                {"url": self._song_path(self._entry("c")), "title": "title c"},
            ],
        )

    def test_get_songs_cached_with_failing_download_returns_empty(self):
        self._write_metadata({"search": self._entry("a")})
        manager = CacheManager()
        self.ydl.download.side_effect = DownloadError("failed")

        self.assertEqual(manager.get_songs("search"), [])
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
