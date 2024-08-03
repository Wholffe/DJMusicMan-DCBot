FFMPEG_OPTIONS = {
  'before_options':
  '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
  'options': '-vn -b:a 192k -bufsize 64k'
}

YDL_OPTIONS = {
  'format': 'bestaudio/best',
  'noplaylist': True,
  'default_search': 'ytsearch'
}