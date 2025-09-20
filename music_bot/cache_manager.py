import json
import os
from typing import Dict, List, Optional

import yt_dlp

from .config import CACHE_DIR, YDLP_OPTIONS


class CacheManager:
    """Handles metadata and song file caching."""

    def __init__(self):
        self.METADATA_CACHE_FILE_PATH = os.path.join(CACHE_DIR, "metadata_cache.json")
        self.metadata_cache = {}
        self._initialize_cache()

    def _initialize_cache(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.metadata_cache = self._load_metadata()

    def _load_metadata(self) -> Dict:
        if not os.path.isfile(self.METADATA_CACHE_FILE_PATH):
            return {}
        try:
            with open(self.METADATA_CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_metadata(self):
        with open(self.METADATA_CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(self.metadata_cache, f, indent=4)

    def _process_entries(self, entries: List[Dict]) -> List[Dict[str, str]]:
        """Builds a list of songs from entries, ensuring files are downloaded."""
        songs = []
        for entry in entries:
            if not entry:
                continue

            filepath = self._download_song_if_missing(entry)
            if filepath:
                songs.append(
                    {
                        "url": filepath,
                        "title": entry.get("title", "Unknown Title"),
                    }
                )
        return songs

    def _download_song_if_missing(self, entry: Dict) -> Optional[str]:
        """Gets the filepath for an entry, downloading the file if it doesn't exist."""
        with yt_dlp.YoutubeDL(YDLP_OPTIONS) as ydl:
            filepath = ydl.prepare_filename(entry)

        if os.path.isfile(filepath):
            return filepath

        download_opts = YDLP_OPTIONS.copy()
        download_opts["skip_download"] = False
        with yt_dlp.YoutubeDL(download_opts) as ydl_dl:
            ydl_dl.download([entry["webpage_url"]])

        return filepath

    def _fetch_and_cache_new_song(self, search: str) -> Optional[Dict]:
        """Fetches info and downloads a new song in one step, then caches it."""
        opts = YDLP_OPTIONS.copy()
        opts["skip_download"] = False
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(search, download=True)

        self.metadata_cache[search] = info
        self._save_metadata()
        return info

    def get_songs(self, search: str) -> List[Dict[str, str]]:
        """
        Main method to get song data using guard clauses for clarity.
        """
        if search in self.metadata_cache:
            info = self.metadata_cache[search]
            entries = info.get("entries", [info])
            return self._process_entries(entries)

        info = self._fetch_and_cache_new_song(search)

        if not info:
            return []

        entries = info.get("entries", [info])
        return self._process_entries(entries)
