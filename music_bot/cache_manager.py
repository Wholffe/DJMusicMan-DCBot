import json
import os

import yt_dlp

from .config import CACHE_DIR, YDLP_OPTIONS


class CacheManager:
    """Handles metadata and song file caching."""

    def __init__(self):
        self.METADATA_CACHE_FILE_PATH = os.path.join(CACHE_DIR, "metadata_cache.json")
        self.metadata_cache = {}
        self._initialize_cache()

    def _initialize_cache(self):
        """Creates the cache directory and loads existing metadata."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.metadata_cache = self._load_metadata()

    def _load_metadata(self) -> dict:
        """Loads the metadata cache from a JSON file."""
        if not os.path.isfile(self.METADATA_CACHE_FILE_PATH):
            return {}
        try:
            with open(self.METADATA_CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_metadata(self):
        """Saves the current metadata cache to a JSON file."""
        with open(self.METADATA_CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata_cache, f, indent=4)

    def _fetch_youtube_info(self, search: str):
        """Fetches video/playlist info from YouTube without downloading."""
        try:
            info_opts = YDLP_OPTIONS.copy()
            info_opts["skip_download"] = True
            with yt_dlp.YoutubeDL(info_opts) as ydl:
                info = ydl.extract_info(search, download=False)
                self.metadata_cache[search] = info
                self._save_metadata()
                return info
        except yt_dlp.utils.DownloadError:
            return None

    def _download_song_if_missing(self, entry: dict) -> str:
        """Downloads the audio file if it's not already in the cache."""
        with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
            filepath = ydl.prepare_filename(entry)

        if os.path.isfile(filepath):
            print(f"File '{filepath}' loaded from cache.")
            return filepath

        print(f"File '{filepath}' not found. Downloading...")
        download_opts = YDLP_OPTIONS.copy()
        download_opts["skip_download"] = False
        with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
            ydl_dl.download([entry["webpage_url"]])
        return filepath

    def get_songs(self, search: str) -> list:
        """
        Main method to get song data.
        It handles fetching metadata and downloading audio files.
        """
        info = self.metadata_cache.get(search)
        if not info:
            info = self._fetch_youtube_info(search)
            if not info:
                return []

        entries = info.get("entries", [info])
        songs = []

        for entry in entries:
            if not entry:
                continue

            final_filepath = self._download_song_if_missing(entry)
            songs.append(
                {
                    "url": final_filepath,
                    "title": entry.get("title", "Unknown Title"),
                }
            )

        return songs
