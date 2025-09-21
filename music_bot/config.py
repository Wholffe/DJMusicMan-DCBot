import os


def get_env_int(varname, default):
    val = os.environ.get(varname, None)
    if val is None or val.strip() == "":
        return default
    return int(val)


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
    "outtmpl": "/app/cache/%(id)s.%(ext)s",
    "cookiefile": "cookies.txt",
}

IDLE_TIMER = {"max_duration_timeout": get_env_int("IDLE_TIMER", 180)}

CACHE_DIR = "/app/cache"

MAX_CACHE_FILES = get_env_int("MAX_CACHE_FILES", 100)
