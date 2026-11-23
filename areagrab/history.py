from __future__ import annotations

import io
import threading
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image


@dataclass
class HistoryItem:
    png: bytes
    thumbnail: Image.Image
    timestamp: datetime
    path: Path | None = None
    width: int = 0
    height: int = 0

    def image(self) -> Image.Image:
        return Image.open(io.BytesIO(self.png)).convert("RGB")


class History:
    """In-memory history of recent screenshots (never written to disk by itself)."""

    def __init__(self, size: int = 10) -> None:
        self._items: deque[HistoryItem] = deque(maxlen=max(1, size))
        self._lock = threading.Lock()

    def add(
        self,
        image: Image.Image,
        png: bytes,
        path: Path | None = None,
    ) -> None:
        thumb = image.copy()
        thumb.thumbnail((96, 96), Image.Resampling.LANCZOS)
        item = HistoryItem(
            png=png,
            thumbnail=thumb,
            timestamp=datetime.now(),
            path=path,
            width=image.width,
            height=image.height,
        )
        with self._lock:
            self._items.appendleft(item)

    def items(self) -> list[HistoryItem]:
        with self._lock:
            return list(self._items)

    def get(self, index: int = 0) -> HistoryItem | None:
        with self._lock:
            if 0 <= index < len(self._items):
                return self._items[index]
            return None

    def clear(self) -> None:
        with self._lock:
            self._items.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)
