from __future__ import annotations

import unittest

from PIL import Image

from areagrab.history import History


class HistoryTests(unittest.TestCase):
    def test_order_and_limit(self) -> None:
        history = History(size=3)
        for index in range(5):
            image = Image.new("RGB", (10 + index, 10 + index), (index, 0, 0))
            history.add(image, b"png", None)
        self.assertEqual(len(history), 3)
        first = history.get(0)
        self.assertIsNotNone(first)
        self.assertEqual(first.width, 14)
        self.assertEqual(first.height, 14)

    def test_clear(self) -> None:
        history = History()
        history.add(Image.new("RGB", (2, 2)), b"x")
        history.clear()
        self.assertEqual(len(history), 0)


if __name__ == "__main__":
    unittest.main()
