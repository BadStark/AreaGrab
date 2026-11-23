from __future__ import annotations

import logging
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from ..constants import APP_NAME, resource_path

log = logging.getLogger(__name__)


def _tolerate_uipi_filter_failure() -> None:
    """pystray treats a failed ChangeWindowMessageFilterEx as fatal.

    On restricted tokens (some sandboxed/service sessions) that call returns
    ERROR_ACCESS_DENIED even though the tray icon itself can still work. Keep
    the icon functional instead of losing the only way to quit/settings.
    """
    try:
        from pystray._util import win32 as pystray_win32

        original = pystray_win32.ChangeWindowMessageFilterEx

        def safe(*args, **kwargs):
            try:
                return original(*args, **kwargs)
            except Exception:
                log.debug("ChangeWindowMessageFilterEx failed; continuing", exc_info=True)
                return True

        pystray_win32.ChangeWindowMessageFilterEx = safe
    except Exception:
        log.debug("Could not patch pystray filter call", exc_info=True)


_tolerate_uipi_filter_failure()


class TrayIcon:
    def __init__(self, app) -> None:
        self.app = app
        self.icon: pystray.Icon | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        image = self._load_image()
        self.icon = pystray.Icon(APP_NAME, image, APP_NAME, self._build_menu())
        self._thread = threading.Thread(target=self._run, name="tray", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        try:
            if self.icon is not None:
                self.icon.run()
        except Exception:
            log.exception("Tray icon failed")

    def _load_image(self) -> Image.Image:
        for name in ("areagrab_v2.png", "areagrab.png"):
            path = resource_path(name)
            try:
                if path.exists():
                    image = Image.open(path).convert("RGBA")
                    if image.size != (64, 64):
                        image = image.resize((64, 64), Image.Resampling.LANCZOS)
                    return image
            except Exception:
                log.exception("Could not load tray icon %s", name)
        image = Image.new("RGBA", (64, 64), (15, 23, 42, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((12, 14, 52, 42), radius=5, outline=(34, 197, 94, 255), width=3)
        draw.text((22, 21), "AG", fill=(34, 197, 94, 255))
        return image

    def _build_menu(self) -> pystray.Menu:
        items: list[pystray.MenuItem] = [
            pystray.MenuItem(
                "Сделать снимок",
                lambda _icon, _item: self.app.post("capture"),
                default=True,
            ),
            pystray.MenuItem(
                "Повторить последнюю область (Ctrl+PrtScr)",
                lambda _icon, _item: self.app.post("repeat"),
                enabled=self.app.last_rect is not None,
            ),
            pystray.MenuItem(
                "Весь экран",
                lambda _icon, _item: self.app.post("capture_full"),
            ),
            pystray.Menu.SEPARATOR,
        ]

        def make_recopy(index: int):
            def recopy_action(_icon, _item):
                self.app.post("recopy", index)

            return recopy_action

        recent_items: list[pystray.MenuItem] = []
        history = self.app.history.items()
        for index, item in enumerate(history[:5]):
            label = item.timestamp.strftime("%H:%M:%S")
            if item.width and item.height:
                label += f"  {item.width}×{item.height}"
            recent_items.append(pystray.MenuItem(label, make_recopy(index)))
        if not recent_items:
            recent_items.append(pystray.MenuItem("Пока пусто", None, enabled=False))
        items.append(pystray.MenuItem("Последние снимки", pystray.Menu(*recent_items)))
        items.extend(
            [
                pystray.MenuItem(
                    "Открыть папку", lambda _icon, _item: self.app.post("folder")
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Настройки…", lambda _icon, _item: self.app.post("settings")
                ),
                pystray.MenuItem(
                    "Пауза горячей клавиши",
                    lambda _icon, _item: self.app.post("toggle_pause"),
                    checked=lambda _item: self.app.hotkeys.paused,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "О программе", lambda _icon, _item: self.app.post("about")
                ),
                pystray.MenuItem("Выход", lambda _icon, _item: self.app.post("quit")),
            ]
        )
        return pystray.Menu(*items)

    def refresh(self) -> None:
        if self.icon is None:
            return
        try:
            self.icon.menu = self._build_menu()
            self.icon.update_menu()
        except Exception:
            log.exception("Could not refresh tray menu")

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                log.exception("Could not stop tray icon")
        self.icon = None
