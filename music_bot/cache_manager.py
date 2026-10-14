import json
import os
from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any, cast

import yt_dlp  # type: ignore[import-untyped]
from yt_dlp.utils import DownloadError, ExtractorError  # type: ignore[import-untyped]

from .config import CACHE_DIR, COOKIES_FILE_PATH, MAX_CACHE_FILES, YDLP_OPTIONS
from .logger import logger

if TYPE_CHECKING:
    # Private names from typeshed's yt-dlp stubs (bundled with pyright)
    from yt_dlp import _Params  # type: ignore[import-untyped]
    from yt_dlp.extractor.common import _InfoDict  # type: ignore[import-untyped]


ProgressHook = Callable[[dict[str, Any]], None]


def _create_ydl(
    download: bool = False, progress_hook: ProgressHook | None = None
) -> yt_dlp.YoutubeDL:
    """Creates a YoutubeDL instance from the configured options."""
    params = {**YDLP_OPTIONS, "skip_download": False} if download else YDLP_OPTIONS
    if progress_hook:
        params = {**params, "progress_hooks": [progress_hook]}
    # Without a cookie file yt-dlp would create one and save stale anonymous
    # session cookies to it, which later leads to HTTP 403 errors
    if os.path.isfile(COOKIES_FILE_PATH):
        params = {**params, "cookiefile": COOKIES_FILE_PATH}
    return yt_dlp.YoutubeDL(cast("_Params", params))


class CacheManager:
    """Handles metadata and song file caching."""

    def __init__(self) -> None:
        self.METADATA_CACHE_FILE_PATH = os.path.join(CACHE_DIR, "metadata_cache.json")
        self.metadata_cache: dict[str, dict[str, Any]] = {}
        self._initialize_cache()

    def _initialize_cache(self) -> None:
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.metadata_cache = self._load_metadata()

    def _load_metadata(self) -> dict[str, dict[str, Any]]:
        if not os.path.isfile(self.METADATA_CACHE_FILE_PATH):
            return {}
        try:
            with open(self.METADATA_CACHE_FILE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_metadata(self) -> None:
        with open(self.METADATA_CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata_cache, f, indent=4)

    def _prune_metadata(self, full_info: Mapping[str, Any]) -> dict[str, Any]:
        """Reduces the full yt-dlp metadata to only the essential keys."""

        def get_essentials(entry: Mapping[str, Any]) -> dict[str, Any]:
            return {
                "id": entry.get("id"),
                "title": entry.get("title"),
                "ext": entry.get("ext"),
                "webpage_url": entry.get("webpage_url"),
            }

        if "entries" in full_info:
            return {"entries": [get_essentials(e) for e in full_info["entries"]]}
        return get_essentials(full_info)

    def _delete_song_files(self, info: dict[str, Any]) -> tuple[int, int]:
        """Deletes the files of a cached entry and returns count and bytes."""
        deleted_files = 0
        total_size = 0
        with _create_ydl() as ydl:
            for entry in info.get("entries", [info]):
                filepath = ydl.prepare_filename(cast("_InfoDict", entry))
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_files += 1
        return deleted_files, total_size

    def _enforce_cache_limit(self) -> None:
        """If the cache is over size, removes the oldest entries (FIFO)."""
        while len(self.metadata_cache) > MAX_CACHE_FILES:
            oldest_key = next(iter(self.metadata_cache))
            self._delete_song_files(self.metadata_cache[oldest_key])
            del self.metadata_cache[oldest_key]

        self._save_metadata()

    def _process_entries(
        self,
        entries: list[dict[str, Any]],
        progress_hook: ProgressHook | None = None,
    ) -> list[dict[str, str]]:
        """Builds a list of songs from entries, ensuring files are downloaded."""
        songs = []
        for entry in entries:
            if not entry:
                continue

            filepath = self._download_song_if_missing(entry, progress_hook)
            if filepath:
                songs.append(
                    {
                        "url": filepath,
                        "title": entry.get("title", "Unknown Title"),
                    }
                )
        return songs

    def _download_song_if_missing(
        self, entry: dict[str, Any], progress_hook: ProgressHook | None = None
    ) -> str | None:
        """Gets the filepath for an entry, downloading the file if it doesn't exist."""
        with _create_ydl() as ydl:
            filepath = ydl.prepare_filename(cast("_InfoDict", entry))

        if os.path.isfile(filepath):
            return filepath

        try:
            with _create_ydl(download=True, progress_hook=progress_hook) as ydl_dl:
                ydl_dl.download([entry["webpage_url"]])
        except (DownloadError, ExtractorError):
            logger.warning(
                f"Failed to download '{entry['webpage_url']}'", exc_info=True
            )
            return None

        return filepath

    def _fetch_and_cache_new_song(
        self, search: str, progress_hook: ProgressHook | None = None
    ) -> dict[str, Any] | None:
        """Fetches info and downloads a new song in one step, then caches it."""
        try:
            with _create_ydl(download=True, progress_hook=progress_hook) as ydl:
                info = ydl.extract_info(search, download=True)
        except (DownloadError, ExtractorError):
            logger.warning(f"Failed to fetch '{search}'", exc_info=True)
            return None

        pruned_info = self._prune_metadata(info)
        self.metadata_cache[search] = pruned_info
        self._enforce_cache_limit()
        return pruned_info

    def get_songs(
        self, search: str, progress_hook: ProgressHook | None = None
    ) -> list[dict[str, str]]:
        """Main method to get song data using guard clauses for clarity."""
        if search in self.metadata_cache:
            info = self.metadata_cache[search]
            return self._process_entries(info.get("entries", [info]), progress_hook)

        new_info = self._fetch_and_cache_new_song(search, progress_hook)
        if not new_info:
            return []
        return self._process_entries(new_info.get("entries", [new_info]), progress_hook)

    def clear_cache(self) -> tuple[int, float]:
        """Clears the entire cache and returns the deleted file count and freed MB."""
        deleted_files = 0
        total_size = 0

        for search in list(self.metadata_cache.keys()):
            files, size = self._delete_song_files(self.metadata_cache[search])
            deleted_files += files
            total_size += size
            del self.metadata_cache[search]

        self._save_metadata()
        return deleted_files, round(total_size / (1024 * 1024), 2)
