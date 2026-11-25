from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "AreaGrab"
APP_ID = "AreaGrab"
APP_VERSION = "1.1.0"
MUTEX_NAME = "AreaGrab_SingleInstance_v1"
WEBSITE_URL = "https://areagrab.com/"
RELEASES_URL = "https://areagrab.com/updates.json"

PROJECT_DIR = Path(__file__).resolve().parent.parent

if getattr(sys, "frozen", False):
    _RESOURCE_BASE = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    PORTABLE_DIR = Path(sys.executable).resolve().parent
else:
    _RESOURCE_BASE = PROJECT_DIR
    PORTABLE_DIR = PROJECT_DIR

# A portable.flag file next to the exe keeps settings/logs inside the app folder.
# This also lets AreaGrab run from a USB stick or a folder where AppData is locked.
IS_PORTABLE = (PORTABLE_DIR / "portable.flag").exists()


def is_pro_preview_package() -> bool:
    return (
        bool(getattr(sys, "frozen", False))
        and IS_PORTABLE
        and (PORTABLE_DIR / "pro-preview.flag").is_file()
    )


def resource_path(name: str) -> Path:
    """Return a bundled resource path (works in source tree and PyInstaller)."""
    return _RESOURCE_BASE / name


def _appdata_dir() -> Path:
    base = os.environ.get("APPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Roaming" / APP_NAME


def _localappdata_dir() -> Path:
    base = os.environ.get("LOCALAPPDATA")
    if base:
        return Path(base) / APP_NAME
    return Path.home() / "AppData" / "Local" / APP_NAME


_config_override = os.environ.get("AREAGRAB_CONFIG_DIR")
_local_override = os.environ.get("AREAGRAB_LOCAL_DIR")

if _config_override:
    CONFIG_DIR = Path(_config_override)
elif IS_PORTABLE:
    CONFIG_DIR = PORTABLE_DIR / "data"
else:
    CONFIG_DIR = _appdata_dir()

if _local_override:
    LOCAL_DIR = Path(_local_override)
elif IS_PORTABLE:
    LOCAL_DIR = PORTABLE_DIR / "data"
else:
    LOCAL_DIR = _localappdata_dir()

SETTINGS_PATH = CONFIG_DIR / "settings.json"
LOG_DIR = LOCAL_DIR / "logs"
if IS_PORTABLE:
    TEMP_DIR = LOCAL_DIR / "temp"
else:
    TEMP_DIR = Path(
        os.environ.get("AREAGRAB_TEMP_DIR", os.environ.get("TEMP", str(LOCAL_DIR / "temp")))
    ) / APP_NAME
