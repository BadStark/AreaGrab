"""Offline interface locale selection and formatting."""
import ctypes
import locale
from ctypes import wintypes

from .i18n_messages import ROWS

LANGUAGES = {
    "auto": "System language",
    "ru": "Русский",
    "en": "English",
    "zh-CN": "简体中文",
    "zh-TW": "繁體中文",
    "es": "Español",
    "pt-BR": "Português (Brasil)",
    "de": "Deutsch",
    "fr": "Français",
    "ja": "日本語",
    "ko": "한국어",
    "tr": "Türkçe",
    "it": "Italiano",
    "pl": "Polski",
}
CODES = tuple(code for code in LANGUAGES if code != "auto")
MESSAGE_KEYS = ROWS.keys()
_LANGUAGE_COLUMNS = {code: index for index, code in enumerate(CODES)}


def windows_ui_locale() -> str:
    """Read the primary Windows display language, independently of regional formats."""
    try:
        kernel32 = ctypes.windll.kernel32
        count, length = wintypes.ULONG(), wintypes.ULONG()
        # MUI_LANGUAGE_NAME requests BCP 47 names in a null-delimited buffer.
        get_languages = kernel32.GetUserPreferredUILanguages
        if get_languages(8, ctypes.byref(count), None, ctypes.byref(length)) and length.value:
            names = ctypes.create_unicode_buffer(length.value)
            if get_languages(8, ctypes.byref(count), names, ctypes.byref(length)):
                return names.value
        return locale.windows_locale.get(kernel32.GetUserDefaultUILanguage(), "en")
    except (AttributeError, OSError):
        return "en"


def resolve_language(value: str = "auto", system_locale: str | None = None) -> str:
    if value != "auto":
        return value if value in _LANGUAGE_COLUMNS else "en"
    if system_locale is None:
        system_locale = windows_ui_locale()
    base, *subtags = system_locale.strip().replace("_", "-").lower().split("-")
    if base == "zh":
        if "hans" in subtags:
            return "zh-CN"
        if any(subtag in ("tw", "hk", "mo", "hant", "cht") for subtag in subtags):
            return "zh-TW"
        return "zh-CN"
    if base == "pt":
        return "pt-BR"
    return base if base in _LANGUAGE_COLUMNS else "en"


def translate(text: str, language: str = "auto", **fields: object) -> str:
    row = ROWS[text]
    message = row[_LANGUAGE_COLUMNS[resolve_language(language)]]
    return message.format_map(fields) if fields else message
