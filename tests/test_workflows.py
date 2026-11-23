from __future__ import annotations

import unittest

from PIL import Image

from areagrab.workflows import MAX_HEIGHT, MAX_STEPS, MAX_WIDTH, compose_steps


class GuideTests(unittest.TestCase):
    def test_preserves_capture_order_and_numbers(self) -> None:
        first = Image.new("RGB", (80, 50), "red")
        second = Image.new("RGB", (100, 60), "blue")
        result = compose_steps([first, second])
        self.assertEqual(result.mode, "RGB")
        self.assertEqual(result.size, (148, 24 * 2 + 2 * 44 + 50 + 60 + 18))
        self.assertEqual(result.getpixel((24 + 10, 24 + 44 + 10)), (255, 0, 0))
        self.assertEqual(result.getpixel((24 + 10, 24 + 44 + 50 + 18 + 44 + 10)), (0, 0, 255))

    def test_downscales_large_captures(self) -> None:
        result = compose_steps([Image.new("RGB", (3000, 2000), "white")])
        self.assertLessEqual(result.width, MAX_WIDTH + 48)
        self.assertLessEqual(result.height, MAX_HEIGHT + 44 + 48)

    def test_rejects_empty_and_excessive_batches(self) -> None:
        with self.assertRaises(ValueError):
            compose_steps([])
        with self.assertRaises(ValueError):
            compose_steps([Image.new("RGB", (2, 2))] * (MAX_STEPS + 1))


if __name__ == "__main__":
    unittest.main()
