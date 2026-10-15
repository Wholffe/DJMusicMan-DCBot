import logging
import unittest
from unittest.mock import AsyncMock, MagicMock

import discord
from discord.ext import commands

import music_bot.constants as CONST
from music_bot.commands import cm_showq, get_latency_color
from music_bot.music_queue import MusicQueue

GREEN = discord.Color.from_rgb(67, 181, 129)
RED = discord.Color.from_rgb(240, 71, 71)


class TestGetLatencyColor(unittest.TestCase):
    def test_zero_latency_is_green(self):
        self.assertEqual(get_latency_color(0), GREEN)

    def test_max_latency_is_red(self):
        self.assertEqual(get_latency_color(500), RED)

    def test_latency_above_max_is_clamped_to_red(self):
        self.assertEqual(get_latency_color(1500), RED)

    def test_negative_latency_is_clamped_to_green(self):
        self.assertEqual(get_latency_color(-50), GREEN)

    def test_half_latency_interpolates(self):
        self.assertEqual(get_latency_color(250), discord.Color.from_rgb(153, 126, 100))


class TestCmShowq(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logging.getLogger("MusicBot").setLevel(logging.CRITICAL + 1)
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.send = AsyncMock()
        self.queue = MusicQueue()
        self.musicbot = MagicMock()
        self.musicbot.queue = self.queue

    def _sent_embed(self) -> discord.Embed:
        return self.ctx.send.call_args[1]["embed"]

    def _fields(self) -> dict[str, str]:
        return {
            str(field.name): str(field.value) for field in self._sent_embed().fields
        }

    async def test_showq_with_current_song_and_empty_queue(self):
        self.queue.add_song("url1", "title1")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        self.ctx.send.assert_called_once()
        self.assertEqual(
            self._fields(),
            {
                "Now Playing": "Current song: title1",
                "Loop Status": "Disabled",
                "Queue": CONST.MESSAGE_QUEUE_EMPTY,
            },
        )

    async def test_showq_with_upcoming_songs_and_loop(self):
        self.queue.add_song("url1", "title1")
        self.queue.add_song("url2", "title2")
        self.queue.add_song("url3", "title3")
        self.queue.get_next_song()
        self.queue.set_loop(True)

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertEqual(fields["Loop Status"], "Enabled")
        self.assertEqual(fields["Up Next"], "1. title2\n2. title3")
        self.assertNotIn("And more...", fields)
        self.assertNotIn("Queue", fields)

    async def test_showq_with_too_many_songs_shows_remaining(self):
        self.queue.add_song("url0", "title0")
        for i in range(100):
            self.queue.add_song(f"url{i}", "x" * 20)
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertEqual(len(fields["Up Next"].splitlines()), 33)
        self.assertEqual(fields["And more..."], "67 more items")

    async def test_showq_with_too_long_first_title_shows_remaining(self):
        self.queue.add_song("url0", "title0")
        self.queue.add_song("url1", "x" * 800)
        self.queue.add_song("url2", "title2")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)

        fields = self._fields()
        self.assertNotIn("Up Next", fields)
        self.assertNotIn("Queue", fields)
        self.assertEqual(fields["And more..."], "2 more items")

    async def test_showq_does_not_modify_queue_embed_template(self):
        self.queue.add_song("url1", "title1")
        self.queue.get_next_song()

        await cm_showq(self.musicbot, self.ctx)
        self.ctx.send.reset_mock()
        await cm_showq(self.musicbot, self.ctx)

        self.assertEqual(len(self._sent_embed().fields), 3)


if __name__ == "__main__":
    unittest.main()
