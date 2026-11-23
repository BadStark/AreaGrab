from __future__ import annotations

import json
import unittest
from pathlib import Path

from support import temp_dir

from areagrab.config import Settings


class SettingsTests(unittest.TestCase):
    def test_defaults(self) -> None:
        settings = Settings.default()
        self.assertTrue(settings.save.enabled)
        self.assertEqual(settings.save.format, "jpg")
        self.assertEqual(settings.hotkeys.capture, "print_screen")
        self.assertFalse(settings.advanced.first_run_done)

    def test_copy_is_independent(self) -> None:
        settings = Settings.default()
        cloned = settings.copy()
        cloned.save.folder = "other"
        cloned.license["key"] = "test"
        self.assertNotEqual(settings.save.folder, cloned.save.folder)
        self.assertNotIn("key", settings.license)

    def test_roundtrip(self) -> None:
        with temp_dir() as tmp:
            path = Path(tmp) / "settings.json"
            settings = Settings.default()
            settings.save.folder = tmp
            settings.save.format = "png"
            settings.hotkeys.capture = "ctrl+shift+4"
            settings.advanced.first_run_done = True
            settings.save_settings(path)

            loaded = Settings.load(path)
            self.assertEqual(loaded.save.folder, tmp)
            self.assertEqual(loaded.save.format, "png")
            self.assertEqual(loaded.hotkeys.capture, "ctrl+shift+4")
            self.assertTrue(loaded.advanced.first_run_done)

    def test_invalid_values_are_clamped(self) -> None:
        raw = {
            "save": {"format": "webp", "jpeg_quality": 999},
            "capture": {"dim": 9},
            "notifications": {"duration_ms": 1},
            "hotkeys": {"capture": ""},
        }
        settings = Settings.from_dict(raw)
        self.assertEqual(settings.save.format, "jpg")
        self.assertEqual(settings.save.jpeg_quality, 100)
        self.assertLessEqual(settings.capture.dim, 0.8)
        self.assertGreaterEqual(settings.notifications.duration_ms, 1500)

    def test_broken_json_falls_back(self) -> None:
        with temp_dir() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{not json", encoding="utf-8")
            settings = Settings.load(path)
            self.assertTrue(settings.save.enabled)
            self.assertTrue(path.exists())
            self.assertTrue(path.with_suffix(".json.broken").exists())


if __name__ == "__main__":
    unittest.main()
