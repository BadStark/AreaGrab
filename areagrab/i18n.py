"""Offline interface locale selection."""
import ctypes
import locale

LANGUAGES = {
    "auto": "🌐 Auto / System",
    "ru": "Русский", "en": "English",
    "zh-CN": "简体中文", "zh-TW": "繁體中文",
    "es": "Español", "pt-BR": "Português (Brasil)",
    "de": "Deutsch", "fr": "Français", "ja": "日本語",
    "ko": "한국어", "tr": "Türkçe", "it": "Italiano", "pl": "Polski",
}

def resolve_language(value="auto", system_locale=None):
    if value != "auto":
        return value if value in LANGUAGES else "en"
    if system_locale is None:
        try:
            system_locale = locale.windows_locale.get(
                ctypes.windll.kernel32.GetUserDefaultUILanguage(), "en")
        except (AttributeError, OSError):
            system_locale = "en"
    tag = system_locale.replace("_", "-").lower()
    base = tag.split("-")[0]
    if base == "zh":
        return "zh-TW" if any(x in tag.split("-") for x in ("tw", "hk", "mo", "hant")) else "zh-CN"
    if base == "pt":
        return "pt-BR"
    return base if base in LANGUAGES and base != "auto" else "en"
