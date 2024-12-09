import asyncio

from .config import IDLE_TIMER
from music_bot import constants as CONST
from .message_handler import MessageHandler


class IdleTimer:
    def __init__(self):
        self.message_handler = MessageHandler()
        self.idle_timer = 0
        self.max_duration_timeout = IDLE_TIMER.get('max_duration_timeout')
        self.timer_task = None

    async def handle_idle(self,ctx):
        """Handles the bot's behavior when the queue is empty."""
        if not self.timer_task:
            self.timer_task = asyncio.create_task(self.start_idle_timer(ctx))
        await self.message_handler.send_info(ctx, CONST.MESSAGE_QUEUE_EMPTY_USE_PLAY)

    async def start_idle_timer(self,ctx):
        """Starts an idle timer to disconnect the bot after inactivity."""
        self.idle_timer = 0

        while ctx.voice_client and self.idle_timer < self.max_duration_timeout:
            await asyncio.sleep(1)
            if ctx.voice_client.is_playing():
                self.timer_task = None
                return
            self.idle_timer += 1

        await ctx.voice_client.disconnect()
        await self.message_handler.send_info(ctx, CONST.MESSAGE_NO_ACTIVITY_TIMEOUT)