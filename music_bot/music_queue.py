import random


class MusicQueue:
    """Handles the song queue for the music bot."""
    def __init__(self):
        self.queue = []

    def add_song(self, url, title):
        self.queue.append((url, title))

    def get_next_song(self):
        return self.queue.pop(0) if self.queue else None

    def clear(self):
        self.queue.clear()

    def is_empty(self):
        return not self.queue

    def list_queue(self):
        return "\n".join([f"{i + 1}. {song[1]}" for i, song in enumerate(self.queue)])
    
    def shuffle_queue(self):
        random.shuffle(self.queue)