import unittest
from unittest.mock import AsyncMock, MagicMock

import discord
from discord.ext import commands

from music_bot.message_handler import MessageHandler


class TestMessageHandler(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.message_handler = MessageHandler()
        self.ctx = MagicMock(spec=commands.Context)
        self.ctx.send = AsyncMock()

    def _sent_embed(self) -> discord.Embed:
        self.ctx.send.assert_called_once()
        return self.ctx.send.call_args[1]["embed"]

    async def test_send_embed_defaults(self):
        await self.message_handler._send_embed(self.ctx, message="hello")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "hello")
        self.assertEqual(embed.color, MessageHandler.COLORS["default"])
        self.assertFalse(embed.title)
        self.assertEqual(len(embed.fields), 0)
        self.assertIsNone(embed.footer.text)

    async def test_send_embed_uses_given_color(self):
        color = discord.Color.from_rgb(1, 2, 3)

        await self.message_handler._send_embed(self.ctx, message="m", color=color)

        self.assertEqual(self._sent_embed().color, color)

    async def test_send_embed_sets_title(self):
        await self.message_handler._send_embed(self.ctx, message="m", title="Title")

        self.assertEqual(self._sent_embed().title, "Title")

    async def test_send_embed_adds_fields_with_defaults(self):
        fields = [
            {"name": "A", "value": "1", "inline": True},
            {"name": "B", "value": "2"},
            {},
        ]

        await self.message_handler._send_embed(self.ctx, fields=fields)

        embed = self._sent_embed()
        self.assertEqual(
            [(f.name, f.value, f.inline) for f in embed.fields],
            [("A", "1", True), ("B", "2", False), ("", "", False)],
        )

    async def test_send_embed_empty_fields_adds_nothing(self):
        await self.message_handler._send_embed(self.ctx, fields=[])

        self.assertEqual(len(self._sent_embed().fields), 0)

    async def test_send_embed_sets_footer(self):
        await self.message_handler._send_embed(self.ctx, footer="footer text")

        self.assertEqual(self._sent_embed().footer.text, "footer text")

    async def test_send_success_uses_success_color(self):
        await self.message_handler.send_success(self.ctx, "ok")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "ok")
        self.assertEqual(embed.color, discord.Color.green())

    async def test_send_error_uses_error_color(self):
        await self.message_handler.send_error(self.ctx, "fail")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "fail")
        self.assertEqual(embed.color, discord.Color.red())

    async def test_send_info_uses_info_color(self):
        await self.message_handler.send_info(self.ctx, "info")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "info")
        self.assertEqual(embed.color, MessageHandler.COLORS["info"])

    async def test_send_embed_returns_sent_message(self):
        sent = MagicMock(spec=discord.Message)
        self.ctx.send.return_value = sent

        result = await self.message_handler._send_embed(self.ctx, message="m")

        self.assertIs(result, sent)

    async def test_send_progress_uses_info_color_and_returns_message(self):
        sent = MagicMock(spec=discord.Message)
        self.ctx.send.return_value = sent

        result = await self.message_handler.send_progress(self.ctx, "progress")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "progress")
        self.assertEqual(embed.color, MessageHandler.COLORS["info"])
        self.assertIs(result, sent)

    async def test_edit_progress_edits_message_with_info_embed(self):
        sent = MagicMock(spec=discord.Message)
        sent.edit = AsyncMock()

        await self.message_handler.edit_progress(sent, "updated")

        sent.edit.assert_awaited_once()
        embed = sent.edit.call_args[1]["embed"]
        self.assertEqual(embed.description, "updated")
        self.assertEqual(embed.color, MessageHandler.COLORS["info"])
        self.ctx.send.assert_not_called()

    async def test_edit_success_edits_message_with_success_embed(self):
        sent = MagicMock(spec=discord.Message)
        sent.edit = AsyncMock()

        await self.message_handler.edit_success(sent, "done")

        sent.edit.assert_awaited_once()
        embed = sent.edit.call_args[1]["embed"]
        self.assertEqual(embed.description, "done")
        self.assertEqual(embed.color, MessageHandler.COLORS["success"])
        self.ctx.send.assert_not_called()

    async def test_edit_error_edits_message_with_error_embed(self):
        sent = MagicMock(spec=discord.Message)
        sent.edit = AsyncMock()

        await self.message_handler.edit_error(sent, "failed")

        sent.edit.assert_awaited_once()
        embed = sent.edit.call_args[1]["embed"]
        self.assertEqual(embed.description, "failed")
        self.assertEqual(embed.color, MessageHandler.COLORS["error"])
        self.ctx.send.assert_not_called()

    async def test_send_raw_uses_default_color(self):
        await self.message_handler.send_raw(self.ctx, "raw")

        embed = self._sent_embed()
        self.assertEqual(embed.description, "raw")
        self.assertEqual(embed.color, MessageHandler.COLORS["default"])

    async def test_send_colored_uses_given_color(self):
        color = discord.Color.from_rgb(1, 2, 3)

        await self.message_handler.send_colored(self.ctx, "colored", color)

        embed = self._sent_embed()
        self.assertEqual(embed.description, "colored")
        self.assertEqual(embed.color, color)

    async def test_send_custom_passes_all_parts(self):
        embed_dict = {
            "title": "Custom",
            "description": "desc",
            "fields": [{"name": "F", "value": "V", "inline": True}],
            "footer": "foot",
            "color": "success",
        }

        await self.message_handler.send_custom(self.ctx, embed_dict)

        embed = self._sent_embed()
        self.assertEqual(embed.title, "Custom")
        self.assertEqual(embed.description, "desc")
        self.assertEqual(
            [(f.name, f.value, f.inline) for f in embed.fields], [("F", "V", True)]
        )
        self.assertEqual(embed.footer.text, "foot")
        self.assertEqual(embed.color, discord.Color.green())

    async def test_send_custom_empty_dict_uses_defaults(self):
        await self.message_handler.send_custom(self.ctx, {})

        embed = self._sent_embed()
        self.assertFalse(embed.title)
        self.assertFalse(embed.description)
        self.assertEqual(len(embed.fields), 0)
        self.assertIsNone(embed.footer.text)
        self.assertEqual(embed.color, MessageHandler.COLORS["default"])

    async def test_send_custom_unknown_color_uses_default(self):
        await self.message_handler.send_custom(self.ctx, {"color": "purple"})

        self.assertEqual(self._sent_embed().color, MessageHandler.COLORS["default"])


if __name__ == "__main__":
    unittest.main()
