import importlib
import os
import unittest
from unittest.mock import patch

import music_bot.config as config


class TestDataDir(unittest.TestCase):
    def setUp(self):
        # The reloads below replace the module values, so restore them afterwards
        self.addCleanup(importlib.reload, config)

    def _reload_config(self, data_dir: str) -> None:
        # A local .env must not change the result
        with (
            patch.dict(os.environ, {"DATA_DIR": data_dir}),
            patch("dotenv.load_dotenv"),
        ):
            importlib.reload(config)

    def test_data_dir_set_is_used(self):
        data_dir = os.path.join("custom", "data")

        self._reload_config(data_dir)

        self.assertEqual(config.DATA_DIR, data_dir)
        self.assertEqual(config.CACHE_DIR, os.path.join(data_dir, "cache"))
        self.assertEqual(
            config.COOKIES_FILE_PATH, os.path.join(data_dir, "cookies.txt")
        )

    def test_data_dir_empty_falls_back_to_default(self):
        self._reload_config("")

        self.assertEqual(config.DATA_DIR, "./data")
        self.assertEqual(config.CACHE_DIR, os.path.join("./data", "cache"))
        self.assertEqual(
            config.COOKIES_FILE_PATH, os.path.join("./data", "cookies.txt")
        )


if __name__ == "__main__":
    unittest.main()
