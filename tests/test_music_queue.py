import unittest
from unittest.mock import MagicMock

from music_bot.music_queue import MusicQueue


class TestMusicQueue(unittest.TestCase):
    def setUp(self):
        self.queue = MusicQueue()

    def _add_songs(self, count: int) -> None:
        for i in range(1, count + 1):
            self.queue.add_song(f"url{i}", f"title{i}")

    def test_new_queue_is_empty(self):
        self.assertTrue(self.queue.is_empty())
        self.assertIsNone(self.queue.current_song)
        self.assertFalse(self.queue.loop)

    def test_add_song_appends_to_end(self):
        self._add_songs(2)

        self.assertEqual(self.queue.queue, [("url1", "title1"), ("url2", "title2")])
        self.assertFalse(self.queue.is_empty())

    def test_add_song_first_inserts_at_front(self):
        self._add_songs(2)

        self.queue.add_song_first("url0", "title0")

        self.assertEqual(self.queue.queue[0], ("url0", "title0"))
        self.assertEqual(len(self.queue.queue), 3)

    def test_get_next_song_pops_first_song(self):
        self._add_songs(2)

        song = self.queue.get_next_song()

        self.assertEqual(song, ("url1", "title1"))
        self.assertEqual(self.queue.current_song, ("url1", "title1"))
        self.assertEqual(self.queue.queue, [("url2", "title2")])

    def test_get_next_song_empty_queue_returns_none(self):
        self.queue.current_song = ("url0", "title0")

        song = self.queue.get_next_song()

        self.assertIsNone(song)
        self.assertIsNone(self.queue.current_song)

    def test_get_next_song_with_loop_repeats_current_song(self):
        self._add_songs(2)
        self.queue.get_next_song()
        self.queue.set_loop(True)

        song = self.queue.get_next_song()

        self.assertEqual(song, ("url1", "title1"))
        self.assertEqual(self.queue.queue, [("url2", "title2")])

    def test_get_next_song_with_loop_and_empty_queue_repeats_current_song(self):
        self._add_songs(1)
        self.queue.get_next_song()
        self.queue.set_loop(True)

        song = self.queue.get_next_song()

        self.assertEqual(song, ("url1", "title1"))
        self.assertTrue(self.queue.is_empty())

    def test_get_next_song_with_loop_without_current_song_pops_first(self):
        self._add_songs(2)
        self.queue.set_loop(True)

        song = self.queue.get_next_song()

        self.assertEqual(song, ("url1", "title1"))
        self.assertEqual(self.queue.queue, [("url2", "title2")])

    def test_get_next_song_without_loop_does_not_requeue_current_song(self):
        self._add_songs(1)
        self.queue.get_next_song()

        song = self.queue.get_next_song()

        self.assertIsNone(song)
        self.assertTrue(self.queue.is_empty())

    def test_skip_current_song_stops_voice_client(self):
        ctx = MagicMock()

        self.queue.skip_current_song(ctx)

        ctx.voice_client.stop.assert_called_once()

    def test_get_next_song_with_loop_after_skip_plays_next_song(self):
        self._add_songs(2)
        self.queue.get_next_song()
        self.queue.set_loop(True)

        self.queue.skip_current_song(MagicMock())
        song = self.queue.get_next_song()

        self.assertEqual(song, ("url2", "title2"))
        self.assertTrue(self.queue.is_empty())
        self.assertTrue(self.queue.loop)

    def test_skip_flag_only_applies_to_one_song(self):
        self._add_songs(3)
        self.queue.get_next_song()
        self.queue.set_loop(True)
        self.queue.skip_current_song(MagicMock())
        self.queue.get_next_song()

        song = self.queue.get_next_song()

        self.assertEqual(song, ("url2", "title2"))
        self.assertEqual(self.queue.queue, [("url3", "title3")])

    def test_get_next_song_after_skip_with_loop_and_empty_queue_returns_none(self):
        self._add_songs(1)
        self.queue.get_next_song()
        self.queue.set_loop(True)

        self.queue.skip_current_song(MagicMock())
        song = self.queue.get_next_song()

        self.assertIsNone(song)
        self.assertIsNone(self.queue.current_song)

    def test_clear_removes_songs_and_current_song(self):
        self._add_songs(2)
        self.queue.get_next_song()

        self.queue.clear()

        self.assertTrue(self.queue.is_empty())
        self.assertIsNone(self.queue.current_song)

    def test_clear_increments_generation(self):
        generation = self.queue.generation

        self.queue.clear()

        self.assertEqual(self.queue.generation, generation + 1)

    def test_add_song_after_inserts_directly_after_anchor(self):
        self._add_songs(2)
        anchor = self.queue.queue[0]

        song = self.queue.add_song_after(anchor, "url0", "title0")

        self.assertEqual(song, ("url0", "title0"))
        self.assertEqual(
            [s[1] for s in self.queue.queue], ["title1", "title0", "title2"]
        )

    def test_add_song_after_without_anchor_inserts_first(self):
        self._add_songs(2)

        self.queue.add_song_after(None, "url0", "title0")

        self.assertEqual(self.queue.queue[0], ("url0", "title0"))

    def test_add_song_after_missing_anchor_inserts_first(self):
        self._add_songs(2)
        anchor = self.queue.get_next_song()

        self.queue.add_song_after(anchor, "url0", "title0")

        self.assertEqual(self.queue.queue, [("url0", "title0"), ("url2", "title2")])

    def test_add_song_after_chained_keeps_order(self):
        self._add_songs(1)

        anchor = self.queue.add_song_after(None, "urlA", "titleA")
        self.queue.add_song_after(anchor, "urlB", "titleB")

        self.assertEqual(
            [s[1] for s in self.queue.queue], ["titleA", "titleB", "title1"]
        )

    def test_add_song_after_duplicate_song_uses_anchor_identity(self):
        self.queue.add_song("url1", "title1")
        anchor = self.queue.add_song_after(None, "url1", "title1")

        self.queue.add_song_after(anchor, "url2", "title2")

        # The equal song queued earlier must not be taken as the anchor
        self.assertEqual(
            self.queue.queue,
            [("url1", "title1"), ("url2", "title2"), ("url1", "title1")],
        )
        self.assertIs(self.queue.queue[0], anchor)

    def test_clear_keeps_loop_flag(self):
        self.queue.set_loop(True)

        self.queue.clear()

        self.assertTrue(self.queue.loop)

    def test_get_current_song_info_without_song_returns_empty_string(self):
        self.assertEqual(self.queue.get_current_song_info(), "")

    def test_get_current_song_info_returns_title(self):
        self._add_songs(1)
        self.queue.get_next_song()

        self.assertEqual(self.queue.get_current_song_info(), "title1")

    def test_list_queue_empty_returns_empty_string(self):
        self.assertEqual(self.queue.list_queue(), "")

    def test_list_queue_returns_numbered_titles(self):
        self._add_songs(3)

        self.assertEqual(self.queue.list_queue(), "1. title1\n2. title2\n3. title3")

    def test_list_queue_excludes_current_song(self):
        self._add_songs(2)
        self.queue.get_next_song()

        self.assertEqual(self.queue.list_queue(), "1. title2")

    def test_list_queue_with_limit_empty_returns_empty_and_zero(self):
        self.assertEqual(self.queue.list_queue_with_limit(), ("", 0))

    def test_list_queue_with_limit_all_songs_fit(self):
        self._add_songs(3)

        songs, remaining = self.queue.list_queue_with_limit()

        self.assertEqual(songs, self.queue.list_queue())
        self.assertEqual(remaining, 0)

    def test_list_queue_with_limit_counts_remaining_songs(self):
        # Each entry "N. titleN" has 9 characters. Separators are not counted.
        self._add_songs(5)

        songs, remaining = self.queue.list_queue_with_limit(max_length=20)

        self.assertEqual(songs, "1. title1\n2. title2")
        self.assertEqual(remaining, 3)

    def test_list_queue_with_limit_boundary_is_exclusive(self):
        # 9 + 9 == 18 reaches the limit, so the second song is not shown.
        self._add_songs(2)

        songs, remaining = self.queue.list_queue_with_limit(max_length=18)

        self.assertEqual(songs, "1. title1")
        self.assertEqual(remaining, 1)

    def test_list_queue_with_limit_stops_at_first_song_that_does_not_fit(self):
        # Listing stops at the first song that exceeds the limit, so later
        # shorter songs are counted as remaining and numbers match positions.
        self.queue.add_song("url1", "a")
        self.queue.add_song("url2", "x" * 50)
        self.queue.add_song("url3", "b")

        songs, remaining = self.queue.list_queue_with_limit(max_length=20)

        self.assertEqual(songs, "1. a")
        self.assertEqual(remaining, 2)

    def test_list_queue_with_limit_default_limit(self):
        for i in range(100):
            self.queue.add_song(f"url{i}", "x" * 20)

        songs, remaining = self.queue.list_queue_with_limit()

        displayed = songs.split("\n")
        self.assertEqual(len(displayed) + remaining, 100)
        self.assertGreater(remaining, 0)
        self.assertLess(sum(len(line) for line in displayed), 800)

    def test_shuffle_queue_keeps_all_songs(self):
        self._add_songs(10)
        original = list(self.queue.queue)

        self.queue.shuffle_queue()

        self.assertEqual(len(self.queue.queue), len(original))
        self.assertCountEqual(self.queue.queue, original)

    def test_toggle_loop_switches_flag(self):
        self.queue.toggle_loop()
        self.assertTrue(self.queue.loop)

        self.queue.toggle_loop()
        self.assertFalse(self.queue.loop)

    def test_set_loop_sets_flag(self):
        self.queue.set_loop(True)
        self.assertTrue(self.queue.loop)

        self.queue.set_loop(False)
        self.assertFalse(self.queue.loop)

    def test_remove_song_valid_index_returns_and_removes_song(self):
        self._add_songs(3)

        removed = self.queue.remove_song(1)

        self.assertEqual(removed, ("url2", "title2"))
        self.assertEqual(self.queue.queue, [("url1", "title1"), ("url3", "title3")])

    def test_remove_song_index_out_of_range_returns_none(self):
        self._add_songs(2)

        self.assertIsNone(self.queue.remove_song(2))
        self.assertEqual(len(self.queue.queue), 2)

    def test_remove_song_negative_index_returns_none(self):
        self._add_songs(2)

        self.assertIsNone(self.queue.remove_song(-1))
        self.assertEqual(len(self.queue.queue), 2)

    def test_remove_song_empty_queue_returns_none(self):
        self.assertIsNone(self.queue.remove_song(0))


if __name__ == "__main__":
    unittest.main()
