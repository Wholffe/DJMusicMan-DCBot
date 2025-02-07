import random


class MusicQueue:
    """Handles the song queue for the music bot."""
    def __init__(self):
        self.queue = []
        self.current_song = None
        self.loop = False

    def add_song(self, url, title) -> None:
        self.queue.append((url, title))

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
        if self.current_song:
            current_song_info = f'Current song: {self.current_song[1]}'
            if self.loop:
                current_song_info += ' (looping)'
            return current_song_info
        return ''

    def list_queue(self) -> str:
        if not self.queue:
            return 'The queue is empty.'
        queue_list = [f"{i + 1}. {song[1]}" for i, song in enumerate(self.queue)]
        return "\n".join(queue_list)
    
    def shuffle_queue(self) -> None:
        random.shuffle(self.queue)
    
    def toggle_loop(self) -> None:
        self.loop = not self.loop