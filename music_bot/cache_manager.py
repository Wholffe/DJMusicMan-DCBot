import json
import os
import functools
import yt_dlp
from .config import CACHE_DIR, MAX_CACHE_FILES, YDLP_OPTIONS
from .logger import logger

def handle_cache_errors(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper

class CacheManager:
    """Handles metadata and song file caching."""

    def __init__(self):
        self.meta_file_path = os.path.join(CACHE_DIR, "metadata_cache.json")
        self.metadata_cache = {}
        self._initialize_cache()

    @handle_cache_errors
    def _initialize_cache(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        self.metadata_cache = self._load_metadata() or {}

    def _load_metadata(self):
        if not os.path.exists(self.meta_file_path):
            return {}
        try:
            with open(self.meta_file_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return {}

    @handle_cache_errors
    def _save_metadata(self):
        with open(self.meta_file_path, "w", encoding="utf-8") as file:
            json.dump(self.metadata_cache, file, indent=4)

    def _get_ydl_opts(self, progress_hook=None):
        opts = YDLP_OPTIONS.copy()
        opts["skip_download"] = False
        if progress_hook:
            opts["progress_hooks"] = [progress_hook]
        return opts

    @handle_cache_errors
    def _find_file_on_disk(self, video_id):
        if not video_id or not os.path.exists(CACHE_DIR):
            return None
        for filename in os.listdir(CACHE_DIR):
            name, _ = os.path.splitext(filename)
            if name == video_id:
                return os.path.join(CACHE_DIR, filename)
        return None

    def _prune_metadata(self, full_info):
        def get_essentials(entry):
            return {"id": entry.get("id"), "title": entry.get("title")}
        entries = full_info.get("entries", [full_info]) if "entries" in full_info else [full_info]
        return {"entries": [get_essentials(e) for e in entries]}

    def get_songs(self, search_query, progress_hook=None):
        info = None
        
        if search_query in self.metadata_cache:
            info = self.metadata_cache[search_query]
        else:
            info = self._fetch_and_cache_new_search(search_query, progress_hook=None) # Hook hier noch nicht nötig

        if not info:
            return []

        entries = info.get("entries", [info])
        if progress_hook and hasattr(progress_hook, 'set_total_items'):
             progress_hook.set_total_items(len(entries))

        return self._process_entries(entries, progress_hook)

    def _process_entries(self, entries, progress_hook=None):
        songs = []
        for entry in entries:
            if progress_hook and hasattr(progress_hook, 'increment_item'):
                 progress_hook.increment_item()

            video_id = entry.get("id")
            title = entry.get("title", "Unknown Title")
            file_path = self._find_file_on_disk(video_id)
            
            if file_path:
                songs.append({"url": file_path, "title": title})
            else:
                new_path = self._download_entry(entry, progress_hook)
                if new_path:
                    songs.append({"url": new_path, "title": title})
        return songs

    @handle_cache_errors
    def _download_entry(self, entry, progress_hook):
        video_id = entry.get("id")
        url = f"https://www.youtube.com/watch?v={video_id}"
        with yt_dlp.YoutubeDL(self._get_ydl_opts(progress_hook)) as ydl:
            ydl.download([url])
        return self._find_file_on_disk(video_id)

    @handle_cache_errors
    def _fetch_and_cache_new_search(self, search_query, progress_hook):
        with yt_dlp.YoutubeDL(self._get_ydl_opts(None)) as ydl:
            info = ydl.extract_info(search_query, download=False)

        pruned_info = self._prune_metadata(info)
        self.metadata_cache[search_query] = pruned_info
        self._enforce_limit()
        self._save_metadata()
        return pruned_info

    @handle_cache_errors
    def _enforce_limit(self):
        while len(self.metadata_cache) > MAX_CACHE_FILES:
            oldest_key = next(iter(self.metadata_cache))
            oldest_info = self.metadata_cache.pop(oldest_key)
            entries = oldest_info.get("entries", [oldest_info])
            for entry in entries:
                path = self._find_file_on_disk(entry.get("id"))
                if path:
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    def clear_cache(self):
        deleted_count = 0
        total_size_mb = 0
        try:
            if os.path.exists(CACHE_DIR):
                for filename in os.listdir(CACHE_DIR):
                    file_path = os.path.join(CACHE_DIR, filename)
                    if os.path.isfile(file_path):
                        total_size_mb += os.path.getsize(file_path)
                        os.remove(file_path)
                        deleted_count += 1
            self.metadata_cache = {}
            self._save_metadata()
        except Exception as e:
            logger.error(f"Error clearing cache: {e}", exc_info=True)
        return deleted_count, round(total_size_mb / (1024 * 1024), 2)