from __future__ import annotations

import argparse
import logging
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox

from PIL import Image, ImageGrab

from . import __version__
from . import clipboard as clipboard_service
from . import storage
from .config import Settings
from .constants import APP_NAME, LOG_DIR, SETTINGS_PATH, WEBSITE_URL
from .history import History
from .hotkeys import HotkeyError, HotkeyManager
from .logging_setup import setup_logging
from .ui.first_run import FirstRunWindow
from .ui.overlay import SelectionOverlay
from .ui.preview import PreviewWindow
from .ui.settings_window import SettingsWindow
from .ui.toast import ToastManager
from .ui.tray import TrayIcon
from .win32_utils import (
    Rect,
    acquire_single_instance,
    enable_dpi_awareness,
    is_fullscreen_foreground,
    open_path,
    open_url,
    set_autostart,
    show_message,
    virtual_screen_rect,
)

log = logging.getLogger(__name__)


@dataclass
class DeliveryResult:
    image: Image.Image
    png: bytes
    path: Path | None
    clipboard_enabled: bool
    clipboard_ok: bool
    clipboard_error: str | None
    save_error: str | None
    point: tuple[int, int]


class AreaGrabApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.args = args
        self.settings = Settings.load()
        if args.reset:
            self.settings = Settings.default()
            self.settings.advanced.first_run_done = True
            self.settings.save_settings()

        self.history = History(self.settings.clipboard.history_size)
        self.last_rect: tuple[int, int, int, int] | None = None
        self.last_image: Image.Image | None = None
        self._events: queue.Queue[tuple[str, object | None]] = queue.Queue()
        self._capture_pending = False
        self._quitting = False
        self._applied_hotkey: str | None = None
        self._poll_after: str | None = None
        self.settings_window: SettingsWindow | None = None
        self.first_run_window: FirstRunWindow | None = None

        self.overlay = SelectionOverlay(
            root,
            on_done=self._on_selection,
            on_cancel=self._on_cancel,
        )
        self.toasts = ToastManager(
            root,
            enabled=self.settings.notifications.toast,
            duration_ms=self.settings.notifications.duration_ms,
        )
        self.tray = TrayIcon(self)
        self.hotkeys = HotkeyManager(lambda: self.post("capture"))

        self.root.report_callback_exception = self._tk_exception

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        log.info("Starting %s %s", APP_NAME, __version__)
        set_autostart(self.settings.advanced.autostart)
        self.overlay.set_dim(self.settings.capture.dim)
        self.tray.start()
        try:
            self.hotkeys.register(self.settings.hotkeys.capture)
            self._applied_hotkey = self.settings.hotkeys.capture
        except HotkeyError as exc:
            log.exception("Hotkey registration failed")
            self.toast(
                "Горячая клавиша недоступна",
                f"Не удалось зарегистрировать {self.settings.hotkeys.capture}: {exc}. "
                "Откройте настройки и выберите другое сочетание.",
            )

        self._poll_after = self.root.after(40, self._poll)

        if not self.settings.advanced.first_run_done:
            self.root.after(350, self.open_first_run)
        elif self.args.settings:
            self.root.after(250, self.open_settings)
        if self.args.capture:
            self.root.after(600, self.request_capture)

    def post(self, kind: str, payload: object | None = None) -> None:
        self._events.put((kind, payload))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._events.get_nowait()
                self._dispatch(kind, payload)
        except queue.Empty:
            pass
        except Exception:
            log.exception("Event loop error")
        if not self._quitting:
            self._poll_after = self.root.after(40, self._poll)

    def _dispatch(self, kind: str, payload: object | None) -> None:
        if kind == "capture":
            self.request_capture()
        elif kind == "repeat":
            self.repeat_last()
        elif kind == "capture_full":
            self.capture_fullscreen()
        elif kind == "settings":
            self.open_settings()
        elif kind == "folder":
            self.open_folder()
        elif kind == "toggle_pause":
            self.toggle_pause()
        elif kind == "about":
            self.show_about()
        elif kind == "quit":
            self.quit()
        elif kind == "recopy":
            self.recopy(int(payload))  # type: ignore[arg-type]
        elif kind == "delivered":
            self._on_delivered(payload)  # type: ignore[arg-type]
        elif kind == "show_preview":
            self._show_preview_payload(payload)
        else:
            log.warning("Unknown event %s", kind)

    # ------------------------------------------------------------- capture

    def request_capture(self) -> None:
        if self._quitting or self._capture_pending or self.overlay.active:
            return
        delay = max(0, self.settings.capture.delay_seconds)
        if delay:
            self._capture_pending = True
            self.root.after(delay * 1000, self._begin_capture)
        else:
            self._begin_capture()

    def _begin_capture(self) -> None:
        self._capture_pending = False
        if self._quitting or self.overlay.active:
            return
        try:
            image = self.grab_screen()
        except Exception as exc:
            log.exception("Screen grab failed")
            self.toast("Не удалось сделать снимок", str(exc))
            return
        self.overlay.set_dim(self.settings.capture.dim)
        self.overlay.show(image)

    def grab_screen(self) -> Image.Image:
        screen = virtual_screen_rect()
        try:
            image = ImageGrab.grab(all_screens=True)
        except TypeError:
            image = ImageGrab.grab(bbox=screen.as_tuple())
        if image.mode != "RGB":
            image = image.convert("RGB")
        return image

    def _on_selection(
        self, full_image: Image.Image, rect: tuple[int, int, int, int]
    ) -> None:
        self.last_rect = rect
        try:
            crop = full_image.crop(rect)
        except Exception:
            log.exception("Crop failed")
            return
        point = (
            virtual_screen_rect().left + (rect[0] + rect[2]) // 2,
            virtual_screen_rect().top + (rect[1] + rect[3]) // 2,
        )
        self._deliver(crop, point)

    def _on_cancel(self, reason: str) -> None:
        if reason == "too-small":
            self.toast("Слишком маленькая область", "Выделите область побольше и попробуйте снова.")

    def _deliver(self, image: Image.Image, point: tuple[int, int]) -> None:
        thread = threading.Thread(
            target=self._deliver_worker,
            args=(image, point),
            name="deliver",
            daemon=True,
        )
        thread.start()

    def _deliver_worker(self, image: Image.Image, point: tuple[int, int]) -> None:
        png = b""
        clipboard_enabled = bool(self.settings.clipboard.copy_image)
        clipboard_ok = not clipboard_enabled
        clipboard_error: str | None = None
        save_error: str | None = None
        path: Path | None = None

        try:
            png = clipboard_service.png_bytes(image)
        except Exception:
            log.exception("PNG encoding failed")

        if clipboard_enabled:
            try:
                clipboard_service.copy_image(image, png)
                clipboard_ok = True
            except Exception as exc:
                clipboard_ok = False
                clipboard_error = str(exc)
                log.exception("Clipboard copy failed")

        try:
            path = storage.save_image(image, self.settings)
        except Exception as exc:
            save_error = str(exc)
            log.exception("Saving image failed")

        if not png:
            try:
                png = clipboard_service.png_bytes(image)
            except Exception:
                log.exception("History PNG encoding failed")

        self.post(
            "delivered",
            DeliveryResult(
                image=image,
                png=png,
                path=path,
                clipboard_enabled=clipboard_enabled,
                clipboard_ok=clipboard_ok,
                clipboard_error=clipboard_error,
                save_error=save_error,
                point=point,
            ),
        )

    def _on_delivered(self, result: DeliveryResult) -> None:
        if self._quitting:
            return
        if result.png:
            try:
                self.history.add(result.image, result.png, result.path)
                self.tray.refresh()
            except Exception:
                log.exception("Could not add history item")

        self.last_image = result.image
        if is_fullscreen_foreground():
            return
        if not self.settings.notifications.toast:
            return

        title, message = self._toast_text(result)
        actions: list[tuple[str, object]] = []
        if result.path is not None:
            path = result.path
            actions.append(("Открыть", lambda p=path: self.open_path(p)))
            actions.append(("Папка", self.open_folder))
        else:
            image = result.image
            actions.append(
                (
                    "Открыть",
                    lambda img=image: self.show_preview(img, None),
                )
            )
            actions.append(("Настройки", self.open_settings))
        if not result.clipboard_ok and result.path is not None:
            image = result.image
            actions.insert(
                0,
                (
                    "Повторить копирование",
                    lambda img=image: self.copy_image_to_clipboard(img),
                ),
            )

        thumb = result.image if self.settings.notifications.thumbnail else None
        self.toasts.show(
            title,
            message,
            thumbnail=thumb,
            actions=actions,  # type: ignore[arg-type]
            point=result.point,
        )

    def _toast_text(self, result: DeliveryResult) -> tuple[str, str]:
        if result.clipboard_enabled and result.clipboard_ok and result.path is not None:
            return "Скопировано и сохранено", f"{result.path.name}\n{result.path.parent}"
        if result.clipboard_enabled and result.clipboard_ok and result.path is None:
            if result.save_error:
                return (
                    "Скопировано в буфер",
                    f"Файл не сохранён: {result.save_error}",
                )
            return (
                "Скопировано в буфер",
                "Файл не сохранялся. Вставьте Ctrl+V в Telegram, письмо или чат.",
            )
        if not result.clipboard_enabled and result.path is not None:
            return (
                "Сохранено",
                f"Копирование в буфер выключено. Файл: {result.path.name}",
            )
        if result.clipboard_enabled and not result.clipboard_ok and result.path is not None:
            return (
                "Файл сохранён",
                f"Буфер недоступен: {result.clipboard_error or 'другое приложение заняло буфер'}. "
                f"Файл: {result.path.name}",
            )
        if not result.clipboard_enabled and result.path is None:
            return (
                "Снимок не сохранён",
                "Копирование в буфер и сохранение в папку выключены. Включите хотя бы одно в настройках.",
            )
        return (
            "Не удалось сохранить",
            result.clipboard_error or result.save_error or "Неизвестная ошибка",
        )

    def repeat_last(self) -> None:
        if self._quitting or self.overlay.active:
            return
        if not self.last_rect:
            self.toast("Повтор недоступен", "Сначала сделайте хотя бы один снимок.")
            return
        try:
            image = self.grab_screen()
            x1, y1, x2, y2 = self.last_rect
            x1 = max(0, min(image.width, x1))
            y1 = max(0, min(image.height, y1))
            x2 = max(0, min(image.width, x2))
            y2 = max(0, min(image.height, y2))
            if x2 - x1 < 2 or y2 - y1 < 2:
                self.toast("Область недоступна", "Конфигурация мониторов изменилась. Выделите область заново.")
                return
            crop = image.crop((x1, y1, x2, y2))
            point = (
                virtual_screen_rect().left + (x1 + x2) // 2,
                virtual_screen_rect().top + (y1 + y2) // 2,
            )
            self._deliver(crop, point)
        except Exception as exc:
            log.exception("Repeat capture failed")
            self.toast("Ошибка", str(exc))

    def capture_fullscreen(self) -> None:
        if self._quitting or self.overlay.active:
            return
        try:
            image = self.grab_screen()
            point = (virtual_screen_rect().left + image.width // 2, virtual_screen_rect().top + image.height // 2)
            self._deliver(image, point)
        except Exception as exc:
            log.exception("Fullscreen capture failed")
            self.toast("Ошибка", str(exc))

    # ------------------------------------------------------------- settings

    def open_settings(self) -> None:
        if self.settings_window is not None:
            try:
                self.settings_window.top.deiconify()
                self.settings_window.top.lift()
                self.settings_window.top.focus_force()
            except tk.TclError:
                self.settings_window = None
            if self.settings_window is not None:
                return
        self.settings_window = SettingsWindow(self)

    def open_first_run(self) -> None:
        if self.first_run_window is not None:
            return
        self.first_run_window = FirstRunWindow(self)

    def settings_changed(self) -> None:
        self.settings.validate()
        self.toasts.configure(
            self.settings.notifications.toast,
            self.settings.notifications.duration_ms,
        )
        self.overlay.set_dim(self.settings.capture.dim)
        set_autostart(self.settings.advanced.autostart)
        self._apply_hotkey()
        self.save_settings()
        self.tray.refresh()

    def _apply_hotkey(self) -> None:
        target = self.settings.hotkeys.capture
        if not target:
            return
        if self.hotkeys.paused:
            self._applied_hotkey = target
            return
        if target == self._applied_hotkey and self.hotkeys.hotkey == target:
            return
        try:
            self.hotkeys.register(target)
            self._applied_hotkey = target
        except HotkeyError as exc:
            log.exception("Could not register hotkey %s", target)
            self.toast(
                "Горячая клавиша недоступна",
                f"{target}: {exc}. Выберите другое сочетание в настройках.",
            )

    def pause_hotkeys(self) -> None:
        self._applied_hotkey = self.hotkeys.last_hotkey or self.settings.hotkeys.capture
        self.hotkeys.pause()
        self.tray.refresh()

    def resume_hotkeys(self) -> None:
        try:
            self.hotkeys.resume(self._applied_hotkey or self.settings.hotkeys.capture)
        except HotkeyError as exc:
            self.toast("Горячая клавиша недоступна", str(exc))
        self.tray.refresh()

    def record_hotkey(self, callback) -> None:
        """Record the next key combination. Callback receives a string or None."""
        self.pause_hotkeys()

        def deliver(key: str | None) -> None:
            self.root.after(0, lambda: callback(key))

        try:
            self.hotkeys.record(deliver)
        except HotkeyError:
            self.resume_hotkeys()
            raise

    def toggle_pause(self) -> None:
        if self.hotkeys.paused:
            self.resume_hotkeys()
            self.toast("Горячая клавиша включена", self.settings.hotkeys.capture, duration_override=1800)
        else:
            self.pause_hotkeys()
            self.toast("Горячая клавиша на паузе", "Включить можно из меню трея.", duration_override=1800)

    def save_settings(self) -> None:
        try:
            self.settings.save_settings()
        except Exception:
            log.exception("Could not save settings")

    def choose_folder(self) -> str | None:
        from tkinter import filedialog

        selected = filedialog.askdirectory(
            parent=self.root,
            initialdir=self.settings.save.folder,
            title="Выберите папку для снимков",
        )
        return selected or None

    def open_folder(self) -> None:
        try:
            folder = storage.target_folder(self.settings)
            storage.ensure_folder(folder)
            open_path(folder)
        except Exception as exc:
            self.toast("Не удалось открыть папку", str(exc))

    def open_logs(self) -> None:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            open_path(LOG_DIR)
        except Exception as exc:
            self.toast("Не удалось открыть логи", str(exc))

    def reset_settings(self) -> None:
        self.settings = Settings.default()
        self.settings.advanced.first_run_done = True
        self._applied_hotkey = None
        self.settings_changed()
        self.toast("Настройки сброшены", "Значения по умолчанию применены.")

    def clear_history(self) -> None:
        self.history.clear()
        self.tray.refresh()

    def recopy(self, index: int) -> None:
        item = self.history.get(index)
        if item is None:
            return
        try:
            image = item.image()
            clipboard_service.copy_image(image, item.png)
            self.last_image = image
            self.toast("Скопировано", "Снимок снова в буфере. Ctrl+V.")
        except Exception as exc:
            log.exception("Recopy failed")
            self.toast("Не удалось скопировать", str(exc))

    def copy_image_to_clipboard(self, image: Image.Image) -> None:
        try:
            clipboard_service.copy_image(image)
            self.toast("Скопировано", "Снимок в буфере. Ctrl+V.")
        except Exception as exc:
            log.exception("Clipboard copy failed")
            self.toast("Не удалось скопировать", str(exc))

    # ------------------------------------------------------------- preview

    def show_preview(self, image: Image.Image, path: Path | None) -> None:
        try:
            PreviewWindow(self, image, path)
        except Exception:
            log.exception("Preview failed")

    def _show_preview_payload(self, payload: object | None) -> None:
        if isinstance(payload, Image.Image):
            self.show_preview(payload, None)

    # ------------------------------------------------------------- misc

    def open_path(self, path: Path | str) -> None:
        open_path(path)

    def show_about(self) -> None:
        messagebox.showinfo(
            f"О {APP_NAME}",
            f"{APP_NAME} {__version__}\n\n"
            "Снимок → Ctrl+V. Без лишних окон.\n\n"
            f"Горячая клавиша: {self.settings.hotkeys.capture}\n"
            f"Папка: {self.settings.save.folder}\n\n"
            f"Сайт: {WEBSITE_URL}",
            parent=self.root,
        )

    def toast(
        self,
        title: str,
        message: str,
        thumbnail: Image.Image | None = None,
        actions: list[tuple[str, object]] | None = None,
        duration_override: int | None = None,
    ) -> None:
        if duration_override is not None:
            old = self.toasts.duration_ms
            self.toasts.duration_ms = duration_override
            try:
                self.toasts.show(title, message, thumbnail=thumbnail, actions=actions)  # type: ignore[arg-type]
            finally:
                self.toasts.duration_ms = old
        else:
            self.toasts.show(title, message, thumbnail=thumbnail, actions=actions)  # type: ignore[arg-type]

    def _tk_exception(self, exc_type, exc_value, exc_tb) -> None:
        log.exception("Tk callback exception", exc_info=(exc_type, exc_value, exc_tb))

    def quit(self) -> None:
        if self._quitting:
            return
        self._quitting = True
        log.info("Quitting")
        try:
            self.save_settings()
        except Exception:
            log.exception("Could not save settings on quit")
        if self.settings.clipboard.clear_on_exit:
            self.history.clear()
        try:
            self.tray.stop()
        except Exception:
            pass
        try:
            self.hotkeys.close()
        except Exception:
            pass
        try:
            if self._poll_after:
                self.root.after_cancel(self._poll_after)
        except Exception:
            pass
        try:
            self.root.quit()
            self.root.destroy()
        except Exception:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--settings", action="store_true", help="open settings")
    parser.add_argument("--capture", action="store_true", help="take a screenshot immediately")
    parser.add_argument("--autostart", action="store_true", help="started by Windows")
    parser.add_argument("--reset", action="store_true", help="reset settings to defaults")
    parser.add_argument("--version", action="store_true", help="print version")
    return parser


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    enable_dpi_awareness()
    args = build_parser().parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return

    if not acquire_single_instance():
        show_message(APP_NAME, "AreaGrab уже запущен. Иконка приложения находится в системном трее.")
        return

    root = tk.Tk()
    root.withdraw()
    try:
        app = AreaGrabApp(root, args)
        app.start()
        root.mainloop()
    except Exception:
        log.exception("Fatal error")
        raise
    finally:
        try:
            root.destroy()
        except Exception:
            pass


if __name__ == "__main__":
    main()
