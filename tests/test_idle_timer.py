import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from discord.ext import commands

import music_bot.constants as CONST
from music_bot.config import IDLE_TIMER
from music_bot.idle_timer import IdleTimer


class TestIdleTimer(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.idle_timer = IdleTimer()
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.voice_client = MagicMock()
        self.ctx.voice_client.disconnect = AsyncMock()
        self.ctx.send = AsyncMock()

    @patch.object(IdleTimer, "start_idle_timer", new_callable=AsyncMock)
    async def test_handle_idle_starts_timer_once_and_sends_info(
        self, mock_start_idle_timer
    ):
        await self.idle_timer.handle_idle(self.ctx)
        first_task = self.idle_timer.timer_task
        await self.idle_timer.handle_idle(self.ctx)

        self.assertIsNotNone(first_task)
        self.assertIs(self.idle_timer.timer_task, first_task)
        self.assertEqual(self.ctx.send.call_count, 2)
        embed = self.ctx.send.call_args[1]["embed"]
        self.assertEqual(embed.description, CONST.MESSAGE_QUEUE_EMPTY_USE_PLAY)

    def test_init_reads_timeout_from_config(self):
        self.assertEqual(
            self.idle_timer.MAX_DURATION_TIMEOUT, IDLE_TIMER["max_duration_timeout"]
        )

    async def test_clear_timer_task_resets_task(self):
        self.idle_timer.timer_task = MagicMock()

        self.idle_timer.clear_timer_task()

        self.assertIsNone(self.idle_timer.timer_task)

    @patch("music_bot.idle_timer.asyncio.sleep", new_callable=AsyncMock)
    async def test_start_idle_timer_without_voice_client_does_nothing(self, mock_sleep):
        self.ctx.voice_client = None
        self.idle_timer.timer_task = MagicMock()

        await self.idle_timer.start_idle_timer(self.ctx)

        mock_sleep.assert_not_called()
        self.ctx.send.assert_not_called()
        self.assertIsNone(self.idle_timer.timer_task)

    @patch("music_bot.idle_timer.asyncio.sleep", new_callable=AsyncMock)
    async def test_start_idle_timer_counts_up_to_timeout(self, mock_sleep):
        self.idle_timer.MAX_DURATION_TIMEOUT = 3
        self.ctx.voice_client.is_playing.return_value = False

        await self.idle_timer.start_idle_timer(self.ctx)

        self.assertEqual(self.idle_timer.current_timer, 3)
        self.assertEqual(mock_sleep.call_count, 3)
        self.ctx.voice_client.disconnect.assert_called_once()
        self.assertIsNone(self.idle_timer.timer_task)


if __name__ == "__main__":
    unittest.main()
