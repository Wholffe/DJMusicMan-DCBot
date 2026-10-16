import json
import os
import threading
import time
from collections.abc import Callable, Generator, Iterator, Mapping
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

# YouTube sporadically answers with HTTP 403, a retry after a short pause usually works
DOWNLOAD_ATTEMPTS = 2
DOWNLOAD_RETRY_DELAY = 3  # seconds


def _report_failed_attempt(url: str, attempt: int, error: Exception) -> None:
    """Logs a failed download attempt and pauses before the retry."""
    if attempt == DOWNLOAD_ATTEMPTS:
        logger.warning(f"Failed to download '{url}': {error}")
        return
    logger.info(f"Retrying download of '{url}' in {DOWNLOAD_RETRY_DELAY}s: {error}")
    time.sleep(DOWNLOAD_RETRY_DELAY)


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
        # Songs are fetched in executor threads, so cache changes and saving must
        # not interleave
        self.lock = threading.Lock()
        # Concurrent downloads of the same video wrote to the same .part file and
        # corrupted it. Keyed by video id, or by search text for searches without
        # an id, so a search and a link to the same video do not share a lock
        self.download_locks: dict[str, threading.Lock] = {}
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
        """If the cache is over size, removes the least recently used entries."""
        while len(self.metadata_cache) > MAX_CACHE_FILES:
            oldest_key = next(iter(self.metadata_cache))
            self._delete_song_files(self.metadata_cache[oldest_key])
            del self.metadata_cache[oldest_key]

        self._save_metadata()

    def _download_lock(self, entry: dict[str, Any]) -> threading.Lock:
        """Returns the download lock for an entry's video id or search text."""
        key = entry.get("id") or entry.get("url")
        with self.lock:
            return self.download_locks.setdefault(key, threading.Lock())

    def _iter_cached_entries(
        self,
        entries: list[dict[str, Any]],
        progress_hook: ProgressHook | None = None,
    ) -> Iterator[dict[str, str]]:
        """Yields songs from cached entries, ensuring files are downloaded."""
        entries = [entry for entry in entries if entry]
        for index, entry in enumerate(entries, start=1):
            # Lets the progress message show the (i/n) counter for playlists
            extra_info = {"playlist_index": index, "n_entries": len(entries)}
            with self._download_lock(entry):
                filepath = self._download_song_if_missing(
                    entry, progress_hook, extra_info
                )
            if filepath:
                yield {
                    "url": filepath,
                    "title": entry.get("title", "Unknown Title"),
                }

    def _download_song_if_missing(
        self,
        entry: dict[str, Any],
        progress_hook: ProgressHook | None = None,
        extra_info: dict[str, Any] | None = None,
    ) -> str | None:
        """Gets the filepath for an entry, downloading the file if it doesn't exist."""
        with _create_ydl() as ydl:
            filepath = ydl.prepare_filename(cast("_InfoDict", entry))

        if os.path.isfile(filepath):
            return filepath

        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                with _create_ydl(download=True, progress_hook=progress_hook) as ydl_dl:
                    ydl_dl.extract_info(
                        entry["webpage_url"], download=True, extra_info=extra_info
                    )
                return filepath
            except (DownloadError, ExtractorError) as error:
                _report_failed_attempt(entry["webpage_url"], attempt, error)
        return None

    def _download_new_entry(
        self, ydl: yt_dlp.YoutubeDL, entry: dict[str, Any], extra_info: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Downloads a new entry, extracting it again before a retry."""
        url = entry.get("webpage_url") or entry.get("url")
        for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
            try:
                if attempt > 1:
                    # The download links of the first extraction may be the ones
                    # YouTube rejected, so the retry gets fresh ones
                    entry = ydl.extract_info(url, download=False, process=False)
                return ydl.process_ie_result(
                    entry, download=True, extra_info=extra_info
                )
            except (DownloadError, ExtractorError) as error:
                _report_failed_attempt(url, attempt, error)
        return None

    def _fetch_and_cache_new_songs(
        self, search: str, progress_hook: ProgressHook | None = None
    ) -> Iterator[dict[str, str]]:
        """Downloads new songs one by one and caches them once all are done."""
        pruned_entries: list[dict[str, Any]] = []
        with _create_ydl(download=True, progress_hook=progress_hook) as ydl:
            try:
                info = ydl.extract_info(search, download=False, process=False)
                if not info:
                    return
                # Only resolves the flat playlist pages, nothing is downloaded yet
                entries = [e for e in info.get("entries", [info]) if e]
            except (DownloadError, ExtractorError) as error:
                logger.warning(f"Failed to fetch '{search}': {error}")
                return

            for index, entry in enumerate(entries, start=1):
                # Lets the progress message show the (i/n) counter for playlists
                extra_info = {"playlist_index": index, "n_entries": len(entries)}
                with self._download_lock(entry):
                    result = self._download_new_entry(ydl, entry, extra_info)
                if not result:
                    continue

                for video in result.get("entries", [result]):
                    pruned_entries.append(self._prune_metadata(video))
                    yield {
                        "url": ydl.prepare_filename(video),
                        "title": video.get("title", "Unknown Title"),
                    }

        # Only reached if the consumer did not stop early
        if not pruned_entries:
            return
        with self.lock:
            self.metadata_cache[search] = {"entries": pruned_entries}
            self._enforce_cache_limit()

    def iter_songs(
        self, search: str, progress_hook: ProgressHook | None = None
    ) -> Generator[dict[str, str], None, None]:
        """Yields song data one by one, downloading each song as needed."""
        with self.lock:
            info = self.metadata_cache.pop(search, None)
            if info is not None:
                # Moves the entry to the end, so the cache limit keeps recent songs
                self.metadata_cache[search] = info
                self._save_metadata()

        if info is not None:
            yield from self._iter_cached_entries(
                info.get("entries", [info]), progress_hook
            )
            return

        yield from self._fetch_and_cache_new_songs(search, progress_hook)

    def clear_cache(self) -> tuple[int, float]:
        """Clears the entire cache and returns the deleted file count and freed MB."""
        deleted_files = 0
        total_size = 0

        with self.lock:
            for search in list(self.metadata_cache.keys()):
                files, size = self._delete_song_files(self.metadata_cache[search])
                deleted_files += files
                total_size += size
                del self.metadata_cache[search]

            self._save_metadata()
        return deleted_files, round(total_size / (1024 * 1024), 2)
