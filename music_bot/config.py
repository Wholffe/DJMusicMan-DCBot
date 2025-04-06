FFMPEG_OPTIONS = {
  'before_options':'-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
  'options': '-vn -b:a 192k -bufsize 64k'
}

YDLP_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'ytsearch',
    'quiet': False,
    'skip_download': True,
    'geo_bypass': True,
    'concurrent_fragment_downloads': 5,
    'max_downloads': 1,
    'no_warnings': True,
    'prefer_ffmpeg': True,
}

IDLE_TIMER = {
  'max_duration_timeout':180 #time in sec
}