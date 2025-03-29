import random


class MusicQueue:
    """Handles the song queue for the music bot."""
    def __init__(self):
        self.queue = []
        self.current_song = None
        self.loop = False

    def add_song(self, url, title) -> None:
        self.queue.append((url, title))

    def add_song_first(self, url, title) -> None:
        self.queue.insert(0, (url, title))

    def get_next_song(self):
        if self.loop and self.current_song:
            self.queue.insert(0, self.current_song)
        self.current_song = self.queue.pop(0) if self.queue else None
        return self.current_song

    def clear(self):
        self.queue.clear()
        self.current_song = None

    def is_empty(self) -> bool:
        return not self.queue

    def get_current_song_info(self) -> str:
        if not self.current_song:
            return ''
        return self.current_song[1]

    def list_queue(self) -> str:
        if not self.queue:
            return ''
        queue_list = [f"{i + 1}. {song[1]}" for i, song in enumerate(self.queue)]
        queue_list = '\n'.join(queue_list)
        return queue_list

    def list_queue_with_limit(self, max_length: int = 800) -> tuple[str, int]:
        if not self.queue:
            return '', 0
        current_length = 0
        displayed_songs = []
        remaining_songs = 0

        for song in self.queue:
            song_str = f"{len(displayed_songs) + 1}. {song[1]}"
            if current_length + len(song_str) >= max_length:
                remaining_songs += 1
            else:
                displayed_songs.append(song_str)
                current_length += len(song_str)

        return '\n'.join(displayed_songs), remaining_songs
    
    def shuffle_queue(self) -> None:
        random.shuffle(self.queue)
    
    def toggle_loop(self) -> None:
        self.loop = not self.loop
    
    def set_loop(self, value: bool) -> None:
        self.loop = value

    def remove_song(self, index):
        if 0 <= index < len(self.queue):
            return self.queue.pop(index)
        return None