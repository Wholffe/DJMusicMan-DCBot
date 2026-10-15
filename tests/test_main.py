import logging
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import discord
from discord.ext import commands

import main
from main import DJMusicMan


class TestSetupHook(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        logging.getLogger("MusicBot").setLevel(logging.CRITICAL + 1)
        # A new bot per test, the module client must not get the cog twice
        self.bot = DJMusicMan(
            command_prefix=commands.when_mentioned,
            help_command=None,
            intents=main.intents,
        )
        patcher = patch.object(
            self.bot.tree, "sync", new_callable=AsyncMock, return_value=[]
        )
        self.mock_sync = patcher.start()
        self.addCleanup(patcher.stop)

    @patch("main.GUILD_ID", 123)
    async def test_setup_hook_with_guild_id_syncs_guild(self):
        await self.bot.setup_hook()

        self.mock_sync.assert_awaited_once()
        guild = self.mock_sync.call_args.kwargs["guild"]
        self.assertEqual(guild.id, 123)
        self.assertIsNotNone(self.bot.tree.get_command("play", guild=guild))

    @patch("main.GUILD_ID", 0)
    async def test_setup_hook_without_guild_id_syncs_globally(self):
        await self.bot.setup_hook()

        self.mock_sync.assert_awaited_once_with()
        self.assertIsNotNone(self.bot.get_cog("MusicBot"))

    @patch("main.GUILD_ID", 0)
    async def test_setup_hook_sync_http_exception_logs_error(self):
        self.mock_sync.side_effect = discord.HTTPException(
            MagicMock(status=403), "Missing Access"
        )

        with self.assertLogs("MusicBot", level=logging.ERROR) as logs:
            await self.bot.setup_hook()

        self.assertEqual(len(logs.records), 1)
        self.assertIsNotNone(self.bot.get_cog("MusicBot"))

    async def test_on_message_does_not_process_commands(self):
        with patch.object(
            self.bot, "process_commands", new_callable=AsyncMock
        ) as mock_process_commands:
            await self.bot.on_message(MagicMock(spec=discord.Message))

        mock_process_commands.assert_not_called()


class TestClient(unittest.TestCase):
    def test_client_allows_guilds_only(self):
        allowed_contexts = main.client.tree.allowed_contexts

        self.assertTrue(allowed_contexts.guild)
        self.assertFalse(allowed_contexts.dm_channel)
        self.assertFalse(allowed_contexts.private_channel)


if __name__ == "__main__":
    unittest.main()
