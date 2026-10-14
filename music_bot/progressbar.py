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
    """Shows yt-dlp download progress in one Discord message per song."""

    def __init__(
        self,
        ctx,
        loop: asyncio.AbstractEventLoop,
        message_handler: MessageHandler,
    ) -> None:
        self.ctx = ctx
        self.loop = loop
        self.message_handler = message_handler
        self.messages: dict[str, discord.Message] = {}
        self.lock = asyncio.Lock()
        self.last_updates: dict[str, float] = {}

    def __call__(self, status: dict[str, Any]) -> None:
        """Receives yt-dlp progress events in the download thread."""
        # The progress display must never abort a download
        try:
            self._handle(status)
        except Exception:
            logger.warning("Failed to handle download progress", exc_info=True)

    def _handle(self, status: dict[str, Any]) -> None:
        """Throttles a progress event and schedules the message update."""
        finished = status["status"] == "finished"
        if not finished and status["status"] != "downloading":
            return

        title = status["info_dict"].get("title", "Unknown Title")
        key = status["info_dict"].get("id", title)
        if finished and key not in self.last_updates:
            return  # file was already cached, nothing was downloaded

        now = time.monotonic()
        last_update = self.last_updates.get(key)
        if (
            not finished
            and last_update is not None
            and now - last_update < CONST.PROGRESS_UPDATE_INTERVAL
        ):
            return
        self.last_updates[key] = now

        total = status.get("total_bytes") or status.get("total_bytes_estimate")
        downloaded = status.get("downloaded_bytes", 0)
        if finished:
            # yt-dlp reports the final size as total_bytes when a download ends
            total = total or downloaded
            downloaded = total

        text = f"{CONST.MESSAGE_DOWNLOADING} {title}\n"
        text += render_progress_bar(downloaded, total)
        # Fire and forget, so the download thread never waits for Discord
        asyncio.run_coroutine_threadsafe(self._update(key, text), self.loop)

    async def _update(self, key: str, text: str) -> None:
        """Sends the progress message for a song or edits it if it exists."""
        async with self.lock:
            try:
                if key in self.messages:
                    await self.message_handler.edit_progress(self.messages[key], text)
                else:
                    self.messages[key] = await self.message_handler.send_progress(
                        self.ctx, text
                    )
            except Exception:
                # The future is never awaited, so errors would otherwise be lost
                logger.warning(
                    f"Failed to update download progress for '{key}'", exc_info=True
                )
