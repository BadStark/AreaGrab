from __future__ import annotations

import logging
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

from PIL import Image

from .config import Settings
from .win32_utils import default_screenshots_folder

log = logging.getLogger(__name__)

_INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_MAX_NAME = 120


def sanitize_name(name: str) -> str:
    name = _INVALID_CHARS.sub("_", name).strip().strip(".")
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"_+", "_", name).strip("_ ")
    return name[:_MAX_NAME] or "AreaGrab"


def render_filename(template: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    result = template
    replacements = {
        "{date}": when.strftime("%Y-%m-%d"),
        "{time}": when.strftime("%H-%M-%S"),
        "{datetime}": when.strftime("%Y-%m-%d_%H-%M-%S"),
    }
    for token, value in replacements.items():
        result = result.replace(token, value)
    # Unknown placeholders are removed rather than creating invalid names.
    result = re.sub(r"\{[a-zA-Z_]+\}", "", result)
    return sanitize_name(result)


def extension_for(settings: Settings) -> str:
    return ".png" if settings.save.format == "png" else ".jpg"


def target_folder(settings: Settings) -> Path:
    folder = (settings.save.folder or "").strip()
    if not folder:
        folder = str(default_screenshots_folder())
    return Path(os.path.expandvars(os.path.expanduser(folder)))


def ensure_folder(folder: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def is_writable(folder: Path) -> tuple[bool, str | None]:
    try:
        ensure_folder(folder)
        fd, probe = tempfile.mkstemp(prefix=".areagrab-", suffix=".tmp", dir=str(folder))
        os.close(fd)
        os.unlink(probe)
        return True, None
    except Exception as exc:
        return False, str(exc)


def unique_path(folder: Path, base: str, ext: str) -> Path:
    candidate = folder / f"{base}{ext}"
    if not candidate.exists():
        return candidate
    for index in range(1, 1000):
        candidate = folder / f"{base}_{index}{ext}"
        if not candidate.exists():
            return candidate
    return folder / f"{base}_{os.getpid()}{ext}"


def save_image(image: Image.Image, settings: Settings) -> Path | None:
    """Save the image atomically. Returns None when local saving is disabled."""
    if not settings.save.enabled:
        return None

    folder = target_folder(settings)
    ensure_folder(folder)
    ext = extension_for(settings)
    base = render_filename(settings.save.filename_template)
    path = unique_path(folder, base, ext)

    fd, tmp_name = tempfile.mkstemp(prefix=".areagrab-", suffix=ext, dir=str(folder))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        if ext == ".jpg":
            image.convert("RGB").save(
                tmp_path, "JPEG", quality=settings.save.jpeg_quality, optimize=True
            )
        else:
            image.save(tmp_path, "PNG", compress_level=6)
        os.replace(tmp_path, path)
        return path
    except Exception:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def folder_size_hint(folder: Path) -> str:
    try:
        return str(folder)
    except Exception:
        return ""
