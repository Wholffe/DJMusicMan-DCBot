import os

from dotenv import load_dotenv

# Loaded here, because the settings below are read when the package is imported
load_dotenv()


def get_env_int(varname: str, default: int) -> int:
    val = os.environ.get(varname, None)
    if val is None or val.strip() == "":
        return default
    return int(val)


STARTUP_CHANNEL_ID = get_env_int("STARTUP_CHANNEL_ID", 0)
GUILD_ID = get_env_int("GUILD_ID", 0)
DATA_DIR = os.environ.get("DATA_DIR") or "./data"
CACHE_DIR = os.path.join(DATA_DIR, "cache")
COOKIES_FILE_PATH = os.path.join(DATA_DIR, "cookies.txt")
PREFERED_AUDIO_FORMAT = "webm"

FFMPEG_OPTIONS = {
    "options": "-vn",
}

YDLP_OPTIONS = {
    "format": f"bestaudio[ext={PREFERED_AUDIO_FORMAT}]/bestaudio/best",
    "noplaylist": True,
    "default_search": "ytsearch",
    "quiet": True,
    "geo_bypass": True,
    "outtmpl": os.path.join(CACHE_DIR, "%(id)s.%(ext)s"),
}

IDLE_TIMER = {"max_duration_timeout": get_env_int("IDLE_TIMER", 180)}

MAX_CACHE_FILES = get_env_int("MAX_CACHE_FILES", 100)
