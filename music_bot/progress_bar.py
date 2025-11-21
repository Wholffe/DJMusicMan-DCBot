import asyncio
import time
from .logger import logger

class ProgressBar:
    def __init__(self, message, loop):
        self.message = message
        self.loop = loop
        self.last_update_time = 0
        self.current_item = 0
        self.total_items = 1

    def set_total_items(self, total):
        """Setzt die Gesamtanzahl der zu ladenden Lieder."""
        self.total_items = total
        self.current_item = 0

    def increment_item(self):
        """Erhöht den Zähler für das aktuelle Lied."""
        self.current_item += 1

    def __call__(self, download_data):
        status = download_data.get("status")
        
        if status == "finished":
            self._schedule_update(1.0, finished=True)
        elif status == "downloading":
            current_time = time.time()
            if current_time - self.last_update_time > 1.5:
                self.last_update_time = current_time
                total_bytes = download_data.get("total_bytes") or download_data.get("total_bytes_estimate", 0)
                
                if total_bytes > 0:
                    downloaded_bytes = download_data.get("downloaded_bytes", 0)
                    current_percentage = downloaded_bytes / total_bytes
                    self._schedule_update(current_percentage)

    def _schedule_update(self, percentage, finished=False):
        asyncio.run_coroutine_threadsafe(
            self._update_async(percentage, finished), 
            self.loop
        )

    async def _update_async(self, percentage, finished):
        if finished:
            progress_bar_visual = "▓" * 20
            status_text = "100%"
        else:
            filled_blocks = int(percentage * 20)
            empty_blocks = 20 - filled_blocks
            progress_bar_visual = "▓" * filled_blocks + "░" * empty_blocks
            status_text = f"{int(percentage * 100)}%"

        playlist_info = ""
        if self.total_items > 1:
            display_current = min(self.current_item + 1, self.total_items)
            playlist_info = f" `({display_current}/{self.total_items})`"

        try:
            if self.message.embeds:
                embed = self.message.embeds[0]
                embed.description = f"**Downloading...**{playlist_info}\n`[{progress_bar_visual}]` **{status_text}**"
                await self.message.edit(embed=embed)
        except Exception as e:
            logger.warning(f"Failed to update progress bar: {e}")