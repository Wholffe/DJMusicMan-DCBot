import asyncio
import time
from typing import Any

import discord

from music_bot import constants as CONST

from .logger import logger
from .message_handler import MessageHandler


def _to_mb(size: float) -> str:
    return f"{size / 1024**2:.1f}"


def render_progress_bar(downloaded: int, total: int | None, width: int = 20) -> str:
    """Renders a text progress bar with percentage and size in MB."""
    if not total:
        return f"{_to_mb(downloaded)} MB"

    ratio = min(downloaded / total, 1.0)
    filled = round(width * ratio)
    bar = "▰" * filled + "▱" * (width - filled)
    return f"{bar}  {ratio:.0%}\n{_to_mb(downloaded)} / {_to_mb(total)} MB"


class DownloadProgress:
    """Shows yt-dlp download progress in one Discord message per command."""

    def __init__(
        self,
        ctx,
        loop: asyncio.AbstractEventLoop,
        message_handler: MessageHandler,
    ) -> None:
        self.ctx = ctx
        self.loop = loop
        self.message_handler = message_handler
        self.message: discord.Message | None = None
        self.lock = asyncio.Lock()
        self.song_key: str | None = None
        self.last_update: float | None = None
        self.done = False

    def __call__(self, status: dict[str, Any]) -> None:
        """Receives yt-dlp progress events in the download thread."""
        # The progress display must never abort a download
        try:
            self._handle(status)
        except Exception:
            logger.warning("Failed to handle download progress", exc_info=True)

    def _handle(self, status: dict[str, Any]) -> None:
        """Throttles a progress event and schedules the message update."""
        # No 100% bar, as finish() replaces it right after: Discord sometimes kept
        # two quick edits of one message out of order and showed the bar instead
        if status["status"] != "downloading":
            return

        info = status["info_dict"]
        title = info.get("title", "Unknown Title")
        key = info.get("id", title)
        new_song = key != self.song_key

        now = time.monotonic()
        if (
            not new_song
            and self.last_update is not None
            and now - self.last_update < CONST.PROGRESS_UPDATE_INTERVAL
        ):
            return
        self.song_key = key
        self.last_update = now

        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        downloaded = status.get("downloaded_bytes", 0)
        # yt-dlp reports the last block as "downloading" too
        if total and downloaded >= total:
            return

        index = info.get("playlist_index")
        count = info.get("n_entries") or info.get("playlist_count")
        # Searches are one-entry playlists, so show the counter for real ones only
        if index and count and count > 1:
            title = f"{title} ({index}/{count})"

        text = f"{CONST.MESSAGE_DOWNLOADING} {title}\n"
        text += render_progress_bar(downloaded, total)
        # Fire and forget, so the download thread never waits for Discord
        asyncio.run_coroutine_threadsafe(self._update(text), self.loop)

    async def _update(self, text: str) -> None:
        """Sends the progress message or edits it if it exists."""
        async with self.lock:
            # A late update must not overwrite the final message
            if self.done:
                return
            try:
                if self.message is not None:
                    await self.message_handler.edit_progress(self.message, text)
                else:
                    self.message = await self.message_handler.send_progress(
                        self.ctx, text
                    )
            except discord.HTTPException:
                logger.warning("Failed to update download progress", exc_info=True)
                # Interaction followups cannot be edited after 15 minutes, send anew
                self.message = None
            except Exception:
                # The future is never awaited, so errors would otherwise be lost
                logger.warning("Failed to update download progress", exc_info=True)

    async def finish(self, message: str, success: bool) -> bool:
        """Turns the progress message into the final message, if one was sent."""
        async with self.lock:
            self.done = True
            if self.message is None:
                return False

            if success:
                edit = self.message_handler.edit_success
            else:
                edit = self.message_handler.edit_error
            try:
                await edit(self.message, message)
            except discord.HTTPException:
                logger.warning("Failed to edit download progress", exc_info=True)
                return False
            return True
