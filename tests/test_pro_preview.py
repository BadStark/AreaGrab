import unittest

from PIL import Image

from areagrab.editor import Mark, render
from areagrab.pro import ProPreview, WEEK_SECONDS


class ProPreviewTests(unittest.TestCase):
    def test_offer_at_milestones_with_cooldown(self):
        state = ProPreview(captures=98)
        self.assertFalse(state.record_capture(100, can_show=True))
        self.assertTrue(state.record_capture(101, can_show=True))
        state.captures = 199
        self.assertFalse(state.record_capture(200, can_show=True))
        state.captures = 199
        self.assertTrue(state.record_capture(101 + WEEK_SECONDS, can_show=True))

    def test_hidden_offer_is_not_replayed_and_limit_is_three(self):
        state = ProPreview(captures=99)
        self.assertFalse(state.record_capture(100, can_show=False))
        self.assertFalse(state.record_capture(101, can_show=True))
        state.captures = 199
        state.show_offers = False
        self.assertFalse(state.record_capture(102, can_show=True))
        self.assertEqual(state.remaining, 3)
        state.exports = 3
        self.assertEqual(state.remaining, 0)

    def test_mask_and_highlighter_flatten_without_modifying_source(self):
        source = Image.new("RGB", (40, 30), "white")
        edited = render(source, [
            Mark("mask", (12, 12), (2, 2), "#ff0000"),
            Mark("highlight", (16, 18), (25, 22), "#ff0000"),
            Mark("arrow", (30, 5), (38, 5), "#ff0000"),
        ])
        self.assertEqual(edited.size, source.size)
        self.assertEqual(source.getpixel((4, 4)), (255, 255, 255))
        self.assertEqual(edited.getpixel((4, 4)), (0, 0, 0))
        self.assertNotEqual(edited.getpixel((19, 20)), (255, 255, 255))
        self.assertEqual(edited.getpixel((38, 5)), (255, 0, 0))
