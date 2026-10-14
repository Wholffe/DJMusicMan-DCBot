import unittest
from unittest.mock import AsyncMock, MagicMock

from discord.ext import commands

from music_bot.command_handler import CommandHandler


class TestHandleErrors(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.message_handler = MagicMock()
        self.message_handler.send_error = AsyncMock()
        self.command_handler = CommandHandler(self.message_handler)
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.send = AsyncMock()
        self.musicbot = MagicMock()

    async def test_handle_errors_success_sends_nothing(self):
        func = AsyncMock(__name__="cm_ok")

        await self.command_handler.handle_errors(func)(self.musicbot, self.ctx, "a")

        func.assert_awaited_once_with(self.musicbot, self.ctx, "a")
        self.message_handler.send_error.assert_not_called()

    async def test_handle_errors_ctx_first_sends_error_to_ctx(self):
        @self.command_handler.handle_errors
        async def cm_failing(ctx):
            raise ValueError("boom")

        await cm_failing(self.ctx)

        self.message_handler.send_error.assert_awaited_once_with(
            self.ctx, 'Command "cm_failing" failed: boom'
        )

    async def test_handle_errors_musicbot_first_sends_error_to_ctx(self):
        @self.command_handler.handle_errors
        async def cm_failing(musicbot, ctx, search):
            raise ValueError("boom")

        await cm_failing(self.musicbot, self.ctx, "query")

        self.message_handler.send_error.assert_awaited_once_with(
            self.ctx, 'Command "cm_failing" failed: boom'
        )

    async def test_handle_errors_without_ctx_logs_and_does_not_raise(self):
        error = ValueError("boom")

        @self.command_handler.handle_errors
        async def cm_failing(musicbot, value):
            raise error

        with self.assertLogs("MusicBot", level="ERROR") as cm:
            await cm_failing(self.musicbot, "value")

        self.message_handler.send_error.assert_not_called()
        self.assertEqual(cm.records[-1].levelname, "ERROR")
        exc_info = cm.records[-1].exc_info
        assert exc_info is not None
        self.assertIs(exc_info[1], error)

    def test_handle_errors_preserves_function_name(self):
        async def cm_named(musicbot, ctx):
            return None

        self.assertEqual(
            self.command_handler.handle_errors(cm_named).__name__, "cm_named"
        )


if __name__ == "__main__":
    unittest.main()
