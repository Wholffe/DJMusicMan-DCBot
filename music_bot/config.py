FFMPEG_OPTIONS = {
    "options": "-vn",
}

YDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": False,
    "skip_download": True,
    "geo_bypass": True,
    "outtmpl": "cache/%(id)s.%(ext)s",
    "cookiefile": "cookies.txt",
}

IDLE_TIMER = {"max_duration_timeout": 180}

CACHE_DIR = "cache"

MAX_CACHE_FILES = 100
