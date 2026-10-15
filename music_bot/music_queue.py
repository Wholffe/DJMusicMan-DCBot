import asyncio
import random

Song = tuple[str, str]  # (url, title)


class MusicQueue:
    """Handles the song queue for the music bot."""

    def __init__(self) -> None:
        self.queue: list[Song] = []
        self.current_song: Song | None = None
        self.loop = False
        self._skip_current = False
        self.generation = 0  # incremented on clear, so running loads can stop
        self.playback_lock = asyncio.Lock()
        self.loading = 0  # number of running load operations

    def add_song(self, url: str, title: str) -> None:
        self.queue.append((url, title))

    def add_song_first(self, url: str, title: str) -> None:
        self.queue.insert(0, (url, title))

    def add_song_after(self, anchor: Song | None, url: str, title: str) -> Song:
        """Inserts a song directly after the anchor, or first if it is gone."""
        song = (url, title)
        # Compare by identity, the same song can be queued more than once
        index = next((i + 1 for i, s in enumerate(self.queue) if s is anchor), 0)
        self.queue.insert(index, song)
        return song

    def get_next_song(self) -> Song | None:
        if self.loop and self.current_song and not self._skip_current:
            self.queue.insert(0, self.current_song)
        self._skip_current = False
        self.current_song = self.queue.pop(0) if self.queue else None
        return self.current_song

    def clear(self) -> None:
        self.queue.clear()
        self.current_song = None
        self.generation += 1

    def is_empty(self) -> bool:
        return not self.queue

    def get_current_song_info(self) -> str:
        if not self.current_song:
            return ""
        return self.current_song[1]

    def list_queue(self) -> str:
        return "\n".join(f"{i + 1}. {song[1]}" for i, song in enumerate(self.queue))

    def list_queue_with_limit(self, max_length: int = 800) -> tuple[str, int]:
        if not self.queue:
            return "", 0
        current_length = 0
        displayed_songs: list[str] = []

        for index, song in enumerate(self.queue, start=1):
            song_str = f"{index}. {song[1]}"
            if current_length + len(song_str) >= max_length:
                break
            displayed_songs.append(song_str)
            current_length += len(song_str)

        return "\n".join(displayed_songs), len(self.queue) - len(displayed_songs)

    def shuffle_queue(self) -> None:
        random.shuffle(self.queue)

    def toggle_loop(self) -> None:
        self.loop = not self.loop

    def set_loop(self, value: bool) -> None:
        self.loop = value

    def skip_current_song(self, ctx) -> None:
        self._skip_current = True
        ctx.voice_client.stop()

    def remove_song(self, index: int) -> Song | None:
        if 0 <= index < len(self.queue):
            return self.queue.pop(index)
        return None
