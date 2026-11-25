from __future__ import annotations

import ast
import re
import string
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from areagrab.i18n import CODES, LANGUAGES, resolve_language, translate
from areagrab.i18n_messages import ROWS

ROOT = Path(__file__).resolve().parents[1]
INSTALLER_LANGUAGES = dict(zip(
    ("russian", "english", "chinesesimplified", "chinesetraditional", "spanish",
     "brazilianportuguese", "german", "french", "japanese", "korean", "turkish",
     "italian", "polish"),
    ("ru", "en", "zh-CN", "zh-TW", "es", "pt-BR", "de", "fr", "ja", "ko", "tr", "it", "pl"),
))


class LocalizationTests(unittest.TestCase):
    def test_all_messages_have_translations_and_matching_placeholders(self):
        self.assertEqual(set(CODES), set(INSTALLER_LANGUAGES.values()))
        self.assertEqual(len(set(LANGUAGES.values())), len(LANGUAGES))
        formatter = string.Formatter()
        for source, row in ROWS.items():
            expected = {name for _, name, _, _ in formatter.parse(source) if name}
            self.assertEqual(len(row), len(CODES), source)
            for code, text in zip(CODES, row):
                with self.subTest(source=source, language=code):
                    self.assertTrue(text.strip())
                    self.assertNotIn("\ufffd", text)
                    fields = {name for _, name, _, _ in formatter.parse(text) if name}
                    self.assertEqual(fields, expected)
                    if code != "ru":
                        self.assertNotEqual(text, source)

    def test_every_interface_message_has_a_catalog_entry(self):
        files = [ROOT / "areagrab/app.py", *(ROOT / "areagrab/ui").glob("*.py")]
        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    if re.search("[А-Яа-яЁё]", node.value):
                        self.assertIn(node.value, ROWS, f"{path.name}:{node.lineno}")

    def test_resolves_windows_languages_and_falls_back_to_english(self):
        for tag, expected in {
            "ru_RU": "ru", "EN-GB": "en", "es-MX": "es", "pt_BR": "pt-BR",
            "de-AT": "de", "fr-CA": "fr", "ja-JP": "ja", "ko-KR": "ko",
            "tr-TR": "tr", "it-IT": "it", "pl-PL": "pl", "zh-Hans": "zh-CN",
            "zh-CN": "zh-CN", "zh-SG": "zh-CN", "zh-CHT": "zh-TW", "zh-TW": "zh-TW",
            "zh-HK": "zh-TW", "zh-MO": "zh-TW", "zh-Hant": "zh-TW",
            "zh-Hans-HK": "zh-CN", "uk-UA": "en", "nl-NL": "en", "": "en",
        }.items():
            with self.subTest(tag=tag):
                self.assertEqual(resolve_language(system_locale=tag), expected)
        with patch("areagrab.i18n.windows_ui_locale", return_value="ko-KR") as ui:
            self.assertEqual(resolve_language("ja"), "ja")
            self.assertEqual(resolve_language("unsupported"), "en")
            ui.assert_not_called()
            self.assertEqual(resolve_language(), "ko")
            ui.assert_called_once()

    def test_interpolates_without_interpreting_user_data_or_template_tokens(self):
        self.assertIn("{date}", translate(
            "Доступно: {date}, {time}, {datetime}. Расширение добавляется автоматически.", "ja",
        ))
        self.assertEqual(
            translate("Файл не сохранён: {error}", "zh-TW", error="{image}.png"),
            "檔案未儲存：{image}.png",
        )

    def test_installer_language_mapping_and_message_coverage(self):
        source = (ROOT / "areagrab_setup.iss").read_text(encoding="utf-8-sig")
        languages = source.split("[Languages]", 1)[1].split("[CustomMessages]", 1)[0]
        codes = re.findall(r'^Name: "(\w+)"', languages, re.MULTILINE)
        self.assertEqual(codes[0], "english")
        self.assertEqual(set(codes), set(INSTALLER_LANGUAGES))
        self.assertEqual(len(codes), len(INSTALLER_LANGUAGES))
        mapping = dict(re.findall(r"Lang = '(\w+)' then Result := '([^']+)'", source))
        self.assertEqual(dict(english="en", **mapping), INSTALLER_LANGUAGES)
        custom = source.split("[CustomMessages]", 1)[1].split("[Tasks]", 1)[0]
        messages = dict(re.findall(r"^(\w+\.\w+)=(.+)$", custom, re.MULTILINE))
        required = set(re.findall(r"CustomMessage\('(\w+)'\)", source)) | {"StartWithWindows"}
        self.assertEqual(set(messages), {f"{name}.{key}" for name in codes for key in required})
        for name in codes:
            for key in ("InstalledVersion", "IncomingVersion"):
                self.assertEqual(messages[f"{name}.{key}"].count("%1"), 1)


@unittest.skipUnless(sys.platform == "win32", "Windows registry and Tk UI")
class WindowsLocalizationTests(unittest.TestCase):
    def test_installer_language_is_used_only_when_settings_do_not_exist(self):
        import json
        from unittest.mock import MagicMock
        from areagrab.config import Settings
        from support import temp_dir

        with temp_dir() as tmp:
            path = Path(tmp) / "settings.json"
            registry = MagicMock()
            registry.QueryValueEx.return_value = ("zh-TW", 1)
            with patch.dict(sys.modules, winreg=registry), patch("areagrab.config.IS_PORTABLE", False):
                settings = Settings.load(path)
                self.assertEqual(settings.advanced.language, "zh-TW")
                settings.advanced.language = "ja"
                settings.save.jpeg_quality = 84
                settings.save_settings(path)
                registry.QueryValueEx.reset_mock()
                registry.QueryValueEx.return_value = ("en", 1)
                self.assertEqual(Settings.load(path).advanced.language, "ja")
                registry.QueryValueEx.assert_not_called()
                legacy = json.loads(path.read_text(encoding="utf-8"))
                del legacy["advanced"]["language"]
                path.write_text(json.dumps(legacy), encoding="utf-8")
                self.assertEqual(Settings.load(path).advanced.language, "auto")
                self.assertEqual(Settings.load(path).save.jpeg_quality, 84)

    def test_repeated_switches_refresh_open_windows_and_tray(self):
        import tkinter as tk
        from PIL import Image
        from areagrab.app import AreaGrabApp, build_parser
        from areagrab.config import Settings
        from areagrab.ui.preview import PreviewWindow

        root = tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        settings = Settings.default()
        settings.advanced.language = "en"
        settings.save.format = "png"
        with patch("areagrab.app.Settings.load", return_value=settings):
            app = AreaGrabApp(root, build_parser().parse_args([]))
        app.open_settings()
        window = app.settings_window
        app.show_about()
        app.open_first_run()
        preview = PreviewWindow(app, Image.new("RGB", (20, 20)))
        root.update()
        with patch("areagrab.app.set_autostart"), patch.object(app, "_apply_hotkey"), \
                patch.object(app, "save_settings"), patch("areagrab.i18n.windows_ui_locale", return_value="fr-FR"):
            for selected in (*CODES, "auto", "en"):
                with self.subTest(language=selected):
                    window.language_box.current(tuple(LANGUAGES).index(selected))
                    self.assertTrue(window._save())
                    root.update()
                    self.assertEqual(app.settings.advanced.language, selected)
                    self.assertEqual(app.settings.save.format, "png")
                    self.assertEqual(window.close_button.cget("text"), app.tr("Закрыть"))
                    self.assertEqual(window.saved_label.cget("text"), app.tr("Сохранено"))
                    self.assertEqual(window.notebook.tab(0, "text"), app.tr("Общие"))
                    self.assertEqual(preview.top.title(), app.tr("AreaGrab — предпросмотр"))
                    self.assertEqual(app._about_window.title(), app.tr("О программе — AreaGrab"))
                    self.assertEqual(app.first_run_window.top.title(),
                                     app.tr("{app} — первый запуск", app="AreaGrab"))
                    self.assertIn(app.tr("Настройки…"), [item.text for item in app.tray._build_menu()])
