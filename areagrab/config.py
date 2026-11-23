from __future__ import annotations

import json
import logging
import os
import tempfile
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .constants import CONFIG_DIR, IS_PORTABLE, SETTINGS_PATH
from .win32_utils import default_screenshots_folder

log = logging.getLogger(__name__)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _bool(value: Any, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return default


def _int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _str(value: Any, default: str) -> str:
    return value if isinstance(value, str) else default


@dataclass
class SaveSettings:
    enabled: bool = True
    folder: str = ""
    format: str = "jpg"  # "jpg" | "png"
    jpeg_quality: int = 95
    filename_template: str = "AreaGrab_{date}_{time}"


@dataclass
class ClipboardSettings:
    copy_image: bool = True
    history_size: int = 10
    clear_on_exit: bool = True


@dataclass
class HotkeySettings:
    capture: str = "print_screen"
    fullscreen: str = ""


@dataclass
class CaptureSettings:
    include_cursor: bool = False
    delay_seconds: int = 0
    dim: float = 0.4
    sound: bool = False


@dataclass
class NotificationSettings:
    toast: bool = True
    duration_ms: int = 2200
    thumbnail: bool = True


@dataclass
class AdvancedSettings:
    autostart: bool = True
    start_minimized: bool = True
    check_updates: bool = True
    language: str = "ru"
    theme: str = "system"
    first_run_done: bool = False


@dataclass
class Settings:
    schema: int = 1
    save: SaveSettings = field(default_factory=SaveSettings)
    clipboard: ClipboardSettings = field(default_factory=ClipboardSettings)
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    capture: CaptureSettings = field(default_factory=CaptureSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    advanced: AdvancedSettings = field(default_factory=AdvancedSettings)
    license: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------ defaults

    @classmethod
    def default(cls) -> "Settings":
        settings = cls()
        if IS_PORTABLE:
            settings.save.folder = str(CONFIG_DIR / "Screenshots")
        else:
            settings.save.folder = str(default_screenshots_folder())
        return settings

    # ------------------------------------------------------------ load/save

    @classmethod
    def load(cls, path: Path | str | None = None) -> "Settings":
        path = Path(path) if path else SETTINGS_PATH
        if not path.exists():
            settings = cls.default()
            settings.save_settings(path)
            return settings
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                raise ValueError("settings root must be an object")
            settings = cls.from_dict(raw)
            settings.validate()
            return settings
        except Exception:
            log.exception("Failed to load settings from %s, using defaults", path)
            try:
                path.replace(path.with_suffix(".json.broken"))
            except Exception:
                pass
            settings = cls.default()
            settings.save_settings(path)
            return settings

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Settings":
        settings = cls()
        settings.schema = _int(raw.get("schema"), 1)

        save = _dict(raw.get("save"))
        settings.save.enabled = _bool(save.get("enabled"), True)
        settings.save.folder = _str(save.get("folder"), "")
        settings.save.format = _str(save.get("format"), "jpg").lower()
        settings.save.jpeg_quality = _int(save.get("jpeg_quality"), 95)
        settings.save.filename_template = _str(
            save.get("filename_template"), "AreaGrab_{date}_{time}"
        )

        clip = _dict(raw.get("clipboard"))
        settings.clipboard.copy_image = _bool(clip.get("copy_image"), True)
        settings.clipboard.history_size = _int(clip.get("history_size"), 10)
        settings.clipboard.clear_on_exit = _bool(clip.get("clear_on_exit"), True)

        hot = _dict(raw.get("hotkeys"))
        settings.hotkeys.capture = _str(hot.get("capture"), "print_screen")
        settings.hotkeys.fullscreen = _str(hot.get("fullscreen"), "")

        cap = _dict(raw.get("capture"))
        settings.capture.include_cursor = _bool(cap.get("include_cursor"), False)
        settings.capture.delay_seconds = _int(cap.get("delay_seconds"), 0)
        settings.capture.dim = _float(cap.get("dim"), 0.4)
        settings.capture.sound = _bool(cap.get("sound"), False)

        notif = _dict(raw.get("notifications"))
        settings.notifications.toast = _bool(notif.get("toast"), True)
        settings.notifications.duration_ms = _int(notif.get("duration_ms"), 2200)
        settings.notifications.thumbnail = _bool(notif.get("thumbnail"), True)

        adv = _dict(raw.get("advanced"))
        settings.advanced.autostart = _bool(adv.get("autostart"), True)
        settings.advanced.start_minimized = _bool(adv.get("start_minimized"), True)
        settings.advanced.check_updates = _bool(adv.get("check_updates"), True)
        settings.advanced.language = _str(adv.get("language"), "ru")
        settings.advanced.theme = _str(adv.get("theme"), "system")
        settings.advanced.first_run_done = _bool(adv.get("first_run_done"), False)

        lic = _dict(raw.get("license"))
        settings.license = dict(lic)

        settings.validate()
        return settings

    def validate(self) -> None:
        if self.save.format not in ("jpg", "jpeg", "png"):
            self.save.format = "jpg"
        if self.save.format == "jpeg":
            self.save.format = "jpg"
        self.save.jpeg_quality = max(50, min(100, self.save.jpeg_quality))
        if not self.save.folder:
            self.save.folder = (
                str(CONFIG_DIR / "Screenshots")
                if IS_PORTABLE
                else str(default_screenshots_folder())
            )
        self.capture.dim = max(0.1, min(0.8, self.capture.dim))
        self.capture.delay_seconds = max(0, min(10, self.capture.delay_seconds))
        self.clipboard.history_size = max(1, min(50, self.clipboard.history_size))
        self.notifications.duration_ms = max(1500, min(10000, self.notifications.duration_ms))
        self.advanced.language = (
            self.advanced.language if self.advanced.language in ("ru", "en") else "ru"
        )
        if self.advanced.theme not in ("system", "light", "dark"):
            self.advanced.theme = "system"
        if not self.save.filename_template.strip():
            self.save.filename_template = "AreaGrab_{date}_{time}"
        if not self.hotkeys.capture.strip():
            self.hotkeys.capture = "print_screen"

    def save_settings(self, path: Path | str | None = None) -> None:
        path = Path(path) if path else SETTINGS_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(self)
        fd, tmp_name = tempfile.mkstemp(
            prefix="settings-", suffix=".tmp", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, ensure_ascii=False, indent=2)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp_name, path)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    def copy(self) -> "Settings":
        return deepcopy(self)
