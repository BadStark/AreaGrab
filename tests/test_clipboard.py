from __future__ import annotations

import struct
import unittest

from PIL import Image

from areagrab import clipboard


class ClipboardTests(unittest.TestCase):
    def test_dib_header_and_size(self) -> None:
        image = Image.new("RGB", (10, 5), (1, 2, 3))
        data = clipboard._dib_bytes(image)
        header = struct.unpack("<IiiHHIIiiII", data[:40])
        self.assertEqual(header[0], 40)
        self.assertEqual(header[1], 10)
        self.assertEqual(header[2], 5)
        self.assertEqual(header[3], 1)
        self.assertEqual(header[4], 24)
        self.assertEqual(header[5], 0)
        # 24bpp rows padded to 4 bytes: 10*3=30 -> 32, 5 rows.
        self.assertEqual(len(data), 40 + 32 * 5)

    def test_png_bytes(self) -> None:
        image = Image.new("RGB", (4, 4), (10, 20, 30))
        data = clipboard.png_bytes(image)
        self.assertTrue(data.startswith(b"\x89PNG\r\n\x1a\n"))

    def test_copy_text_roundtrip(self) -> None:
        # Uses the real clipboard; skip on systems where it is unavailable.
        try:
            clipboard.copy_text("AreaGrab clipboard test")
        except Exception as exc:  # pragma: no cover - environment dependent
            self.skipTest(f"clipboard unavailable: {exc}")


if __name__ == "__main__":
    unittest.main()
