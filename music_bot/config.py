import os


def get_env_int(varname, default):
    val = os.environ.get(varname, None)
    if val is None or val.strip() == "":
        return default
    return int(val)


DATA_DIR = "/data"
CACHE_DIR = os.path.join(DATA_DIR, "cache")
AUDIO_FORMAT = "m4a"
AUDIO_BITRATE = get_env_int("AUDIO_BITRATE", 192)

FFMPEG_OPTIONS = {
    "options": "-vn",
}

YDLP_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": True,
    "skip_download": True,
    "geo_bypass": True,
    "outtmpl": os.path.join(CACHE_DIR, "%(id)s.%(ext)s"),
    "cookiefile": os.path.join(DATA_DIR, "cookies.txt"),
    "postprocessors": [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": AUDIO_FORMAT,
            "preferredquality": str(AUDIO_BITRATE),
        }
    ],
}

IDLE_TIMER = {"max_duration_timeout": get_env_int("IDLE_TIMER", 180)}

MAX_CACHE_FILES = get_env_int("MAX_CACHE_FILES", 100)
