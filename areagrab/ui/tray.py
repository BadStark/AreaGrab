from __future__ import annotations

import logging
import threading
from pathlib import Path

import pystray
from PIL import Image, ImageDraw

from ..i18n import translate
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
                lambda _item: "Сделать снимок (" + ("PrtScr" if self.app.settings.hotkeys.capture == "print_screen" else self.app.settings.hotkeys.capture) + ")",
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

        # Native Windows tray menus support nested text menus, not embedded thumbnails.
        # Paginate the RAM history so older entries remain reachable.
        items.append(pystray.MenuItem(
            translate("Последние снимки", self.app.settings.advanced.language),
            pystray.Menu(lambda: self._history_page(0)),
            enabled=lambda _item: bool(self.app.history.items()),
        ))
        items.extend(
            [
                pystray.MenuItem(
                    translate("Открыть папку", self.app.settings.advanced.language), lambda _icon, _item: self.app.post("folder")
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    translate("Настройки…", self.app.settings.advanced.language), lambda _icon, _item: self.app.post("settings")
                ),
                pystray.MenuItem(
                    lambda _item: "Возобновить работу AreaGrab" if self.app.hotkeys.paused else "Приостановить работу AreaGrab",
                    lambda _icon, _item: self.app.post("toggle_pause"),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    translate("О программе", self.app.settings.advanced.language), lambda _icon, _item: self.app.post("about")
                ),
                pystray.MenuItem(translate("Выход", self.app.settings.advanced.language), lambda _icon, _item: self.app.post("quit")),
            ]
        )
        return pystray.Menu(*items)

    def _history_page(self, page: int) -> tuple:
        entries = self.app.history.items()
        page_size = 8
        start = page * page_size
        menu = []
        def open_shot(index: int):
            def action(icon, item):
                self.app.post("history_open", index)
            return action

        if not entries:
            return (pystray.MenuItem("Нет снимков", None, enabled=False),)
        for index in range(start, min(start + page_size, len(entries))):
            shot = entries[index]
            label = (
                f"{shot.timestamp:%d.%m %H:%M:%S} · "
                f"{shot.width}×{shot.height}"
            )
            menu.append(pystray.MenuItem(
                label,
                open_shot(index),
            ))
        if start + page_size < len(entries):
            menu.append(pystray.MenuItem(
                "Более старые →",
                pystray.Menu(lambda: self._history_page(page + 1)),
            ))
        return tuple(menu)

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
