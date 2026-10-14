import unittest
from collections.abc import Callable
from typing import Any, cast
from unittest.mock import MagicMock

from music_bot import logger as logger_module

# music_bot.logger rebinds `log_command` to the decorator bound to the module
# logger, but type checkers still see the factory signature.
log_command = cast(
    Callable[[Callable[..., Any]], Callable[..., Any]], logger_module.log_command
)


class TestLogCommand(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.ctx = MagicMock()
        self.ctx.author = "user#1"
        self.musicbot = MagicMock()

    async def test_log_command_returns_result_and_logs(self):
        @log_command
        async def cm_example(musicbot, ctx, *args, **kwargs):
            return (musicbot, ctx, args, kwargs)

        with self.assertLogs("MusicBot", level="INFO") as cm:
            result = await cm_example(self.musicbot, self.ctx, "a", key="b")

        self.assertEqual(result, (self.musicbot, self.ctx, ("a",), {"key": "b"}))
        self.assertEqual(
            [record.getMessage() for record in cm.records],
            [
                "User 'user#1' executed command 'cm_example' with args: ('a',)",
                "Finished 'cm_example' execution by user 'user#1'.",
            ],
        )

    async def test_log_command_logs_and_reraises_errors(self):
        @log_command
        async def cm_failing(musicbot, ctx):
            raise ValueError("boom")

        with (
            self.assertLogs("MusicBot", level="INFO") as cm,
            self.assertRaises(ValueError),
        ):
            await cm_failing(self.musicbot, self.ctx)

        self.assertEqual(cm.records[-1].levelname, "ERROR")
        self.assertEqual(
            cm.records[-1].getMessage(),
            "Error executing command 'cm_failing' for user 'user#1': boom",
        )
        self.assertIsNotNone(cm.records[-1].exc_info)

    def test_log_command_preserves_function_name(self):
        async def cm_named(musicbot, ctx):
            return None

        self.assertEqual(log_command(cm_named).__name__, "cm_named")


if __name__ == "__main__":
    unittest.main()
