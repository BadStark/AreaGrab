"""Capture references for sharing the exact bytes selected by the user."""
from __future__ import annotations

from dataclasses import dataclass
from os import stat_result
from pathlib import Path


def file_identity(info: stat_result) -> tuple[int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


@dataclass(frozen=True)
class ShareSource:
    png: bytes
    path: Path | None
    identity: tuple[int, int, int, int] | None = None
