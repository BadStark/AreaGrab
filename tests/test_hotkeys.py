from __future__ import annotations

import unittest

from areagrab.hotkeys import HotkeyError, parse_hotkey, validate_hotkey


class HotkeyTests(unittest.TestCase):
    def test_print_screen(self) -> None:
        binding = parse_hotkey("print_screen")
        self.assertEqual(binding.hotkey, "print_screen")
        self.assertEqual(binding.key_vk, 0x2C)
        self.assertFalse(binding.ctrl)

    def test_combinations(self) -> None:
        binding = parse_hotkey("Ctrl+Shift+4")
        self.assertEqual(binding.hotkey, "ctrl+shift+4")
        self.assertTrue(binding.ctrl)
        self.assertTrue(binding.shift)
        self.assertEqual(binding.key_vk, 0x34)

    def test_repeat_shortcut(self) -> None:
        binding = parse_hotkey("ctrl+print_screen")
        self.assertEqual(binding.key_vk, 0x2C)
        self.assertTrue(binding.ctrl)
        self.assertFalse(binding.alt)
        self.assertFalse(binding.shift)

    def test_function_key(self) -> None:
        self.assertEqual(parse_hotkey("f12").key_vk, 0x7B)

    def test_invalid(self) -> None:
        self.assertFalse(validate_hotkey("ctrl+shift"))
        with self.assertRaises(HotkeyError):
            parse_hotkey("ctrl+shift")
        with self.assertRaises(HotkeyError):
            parse_hotkey("ctrl+unknown")


if __name__ == "__main__":
    unittest.main()
