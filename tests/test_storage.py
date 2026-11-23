from __future__ import annotations

import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from support import temp_dir

from PIL import Image

from areagrab.config import Settings
from areagrab.storage import (
    ensure_folder,
    is_writable,
    render_filename,
    sanitize_name,
    save_image,
    target_folder,
    unique_path,
)


class StorageTests(unittest.TestCase):
    def test_sanitize(self) -> None:
        self.assertEqual(sanitize_name('a<b>c:d/e\\f|g?h*i'), "a_b_c_d_e_f_g_h_i")
        self.assertEqual(sanitize_name("  ...  "), "AreaGrab")
        self.assertLessEqual(len(sanitize_name("x" * 500)), 120)

    def test_template(self) -> None:
        name = render_filename("AreaGrab_{date}_{time}")
        self.assertTrue(name.startswith("AreaGrab_"))
        self.assertNotIn("{", name)
        self.assertNotIn(":", name)

    def test_unique_path(self) -> None:
        with temp_dir() as tmp:
            folder = Path(tmp)
            first = unique_path(folder, "shot", ".png")
            first.write_bytes(b"x")
            second = unique_path(folder, "shot", ".png")
            self.assertNotEqual(first, second)
            self.assertTrue(second.name.startswith("shot_1"))

    def test_save_disabled(self) -> None:
        settings = Settings.default()
        settings.save.enabled = False
        self.assertIsNone(save_image(Image.new("RGB", (10, 10)), settings))

    def test_save_png_and_jpg(self) -> None:
        with temp_dir() as tmp:
            settings = Settings.default()
            settings.save.folder = tmp
            settings.save.enabled = True
            settings.save.filename_template = "test_{date}_{time}"

            settings.save.format = "png"
            png_path = save_image(Image.new("RGB", (32, 24), (10, 20, 30)), settings)
            self.assertIsNotNone(png_path)
            self.assertTrue(png_path.exists())
            with Image.open(png_path) as saved:
                self.assertEqual(saved.size, (32, 24))

            settings.save.format = "jpg"
            jpg_path = save_image(Image.new("RGB", (32, 24), (10, 20, 30)), settings)
            self.assertIsNotNone(jpg_path)
            self.assertTrue(jpg_path.exists())
            self.assertEqual(jpg_path.suffix, ".jpg")

    def test_parallel_saves_do_not_overwrite(self) -> None:
        with temp_dir() as tmp:
            settings = Settings.default()
            settings.save.folder = tmp
            settings.save.format = "png"
            settings.save.filename_template = "same-name"
            def save(index: int):
                return save_image(Image.new("RGB", (8, 8), (index, 0, 0)), settings)
            with ThreadPoolExecutor(max_workers=8) as executor:
                paths = list(executor.map(save, range(20)))
            self.assertEqual(len(set(paths)), 20)
            for path in paths:
                self.assertTrue(path.exists())

    def test_folder_helpers(self) -> None:
        with temp_dir() as tmp:
            folder = Path(tmp) / "nested"
            ensure_folder(folder)
            self.assertTrue(folder.is_dir())
            ok, error = is_writable(folder)
            self.assertTrue(ok, error)

    def test_target_folder_fallback(self) -> None:
        settings = Settings.default()
        settings.save.folder = ""
        self.assertTrue(str(target_folder(settings)))


if __name__ == "__main__":
    unittest.main()
