from __future__ import annotations

import argparse
import logging
import queue
import sys
import threading
import time
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import ttk

from PIL import Image, ImageGrab

from . import __version__
from . import clipboard as clipboard_service
from . import storage
from .config import Settings
from .share_source import ShareSource, file_identity
from .constants import APP_NAME, LOG_DIR, SETTINGS_PATH, WEBSITE_URL
from .history import History
from .installer_shutdown import listen_for_installer_shutdown
from .hotkeys import HotkeyError, HotkeyManager
from .logging_setup import setup_logging
from .ui.first_run import FirstRunWindow
from .i18n import resolve_language, translate
from .ui.localization import LocalizedDialog, capture_labels, update_labels
from .ui.overlay import SelectionOverlay
from .ui.preview import PreviewWindow
from .ui.pro_window import EditorWindow, show_plans
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
    share_source: ShareSource


class AreaGrabApp:
    def __init__(self, root: tk.Tk, args: argparse.Namespace) -> None:
        self.root = root
        self.args = args
        self.settings = Settings.load()
        if args.reset:
            previous = self.settings
            self.settings = Settings.default()
            self.settings.pro_preview = previous.pro_preview
            self.settings.license = previous.license
            self.settings.advanced.first_run_done = True
            self.settings.save_settings()

        self._capture_stats_after: str | None = None
        self._language = resolve_language(self.settings.advanced.language)
        self.history = History(self.settings.clipboard.history_size)
        self.last_rect: tuple[int, int, int, int] | None = None
        self.last_image: Image.Image | None = None
        self._share_window: tk.Toplevel | None = None
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
            translate=self.tr,
        )
        self.toasts = ToastManager(
            root,
            enabled=self.settings.notifications.toast,
            duration_ms=self.settings.notifications.duration_ms,
        )
        self.tray = TrayIcon(self)
        self.hotkeys = HotkeyManager(
            lambda: self.post("capture"),
            lambda: self.post("repeat"),
        )

        self.root.report_callback_exception = self._tk_exception

    @property
    def interface_language(self) -> str:
        return self._language

    @property
    def can_share(self) -> bool:
        return self.args.preview_pro and self.settings.lan_share.enabled

    def tr(self, text: str, **fields: object) -> str:
        return translate(text, self._language, **fields)

    def error_text(self, error: object = None) -> str:
        if str(error) == "clipboard is busy":
            return self.tr("Буфер обмена занят.")
        return self.tr("Операция не выполнена. Подробности в логах AreaGrab.")

    # ------------------------------------------------------------- lifecycle

    def start(self) -> None:
        log.info("Starting %s %s", APP_NAME, __version__)
        set_autostart(self.settings.advanced.autostart)
        self.overlay.set_dim(self.settings.capture.dim)
        self.tray.start()
        listen_for_installer_shutdown(lambda: self.post("quit"))
        try:
            self.hotkeys.register(self.settings.hotkeys.capture)
            self._applied_hotkey = self.settings.hotkeys.capture
        except HotkeyError as exc:
            log.exception("Hotkey registration failed")
            self.toast(
                self.tr('Горячая клавиша недоступна'),
                self.tr('Не удалось зарегистрировать {shortcut}: {error}. Откройте настройки и выберите другое сочетание.', shortcut=self.settings.hotkeys.capture, error=self.error_text(exc)),
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
        elif kind == "pro":
            self.open_pro()
        elif kind == "share":
            self.open_share(payload)
        elif kind == "history_edit":
            try:
                self.open_editor(payload.image())
            except Exception as exc:
                log.exception("Could not open screenshot in the editor")
                self.toast(self.tr("Не удалось открыть снимок"), self.error_text(exc))
        elif kind == "folder":
            self.open_folder()
        elif kind == "history_open":
            self.open_history_item(int(payload))
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
            self.toast(self.tr('Не удалось сделать снимок'), self.error_text(exc))
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
            self.toast(self.tr('Слишком маленькая область'), self.tr('Выделите область побольше и попробуйте снова.'))

    def _deliver(self, image: Image.Image, point: tuple[int, int]) -> None:
        # Freeze options at capture time; settings can change while the worker runs.
        settings = self.settings.copy()
        thread = threading.Thread(
            target=self._deliver_worker,
            args=(image, point, settings),
            name="deliver",
            daemon=True,
        )
        thread.start()

    def _deliver_worker(self, image: Image.Image, point: tuple[int, int], settings: Settings) -> None:
        png = b""
        clipboard_enabled = bool(settings.clipboard.copy_image)
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
            path = storage.save_image(image, settings)
        except Exception as exc:
            save_error = str(exc)
            log.exception("Saving image failed")

        if not png:
            try:
                png = clipboard_service.png_bytes(image)
            except Exception:
                log.exception("History PNG encoding failed")

        identity = None
        if path is not None and self.args.preview_pro:
            try:
                identity = file_identity(path.stat())
            except OSError:
                pass

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
                share_source=ShareSource(png, path, identity),
            ),
        )

    def _on_delivered(self, result: DeliveryResult) -> None:
        if self._quitting:
            return
        if result.png:
            try:
                self.history.add(result.image, result.png, result.path, result.share_source)
                self.tray.refresh()
            except Exception:
                log.exception("Could not add history item")

        self.last_image = result.image
        can_show = self.settings.notifications.toast and not is_fullscreen_foreground()
        offer = False
        if (result.clipboard_enabled and result.clipboard_ok) or result.path is not None:
            offer = self.settings.pro_preview.record_capture(int(time.time()), can_show=can_show)
            if self._capture_stats_after is None:
                self._capture_stats_after = self.root.after(500, self._save_capture_stats)
        if not can_show:
            return

        title, message = self._toast_text(result)
        actions: list[tuple[str, object]] = []
        if result.path is not None:
            path = result.path
            actions.append((self.tr('Открыть'), lambda p=path: self.open_path(p)))
            actions.append((self.tr('Папка'), self.open_folder))
        else:
            image = result.image
            actions.append(
                (
                    self.tr('Открыть'),
                    lambda img=image: self.show_preview(img, None),
                )
            )
            actions.append((self.tr('Настройки'), self.open_settings))
        if not result.clipboard_ok and result.path is not None:
            image = result.image
            actions.insert(
                0,
                (
                    self.tr('Повторить копирование'),
                    lambda img=image: self.copy_image_to_clipboard(img),
                ),
            )

        if self.can_share and self.settings.lan_share.show_in_toast and (result.png or result.path):
            actions.append((self.tr("Отправить на устройство"),
                            lambda source=result.share_source: self.open_share(source)))

        if offer:
            actions.append((self.tr("Перейти на Pro"),
                            lambda img=result.image: self.open_pro(img)))

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
            return self.tr('Скопировано и сохранено'), f"{result.path.name}\n{result.path.parent}"
        if result.clipboard_enabled and result.clipboard_ok and result.path is None:
            if result.save_error:
                return (
                    self.tr('Скопировано в буфер'),
                    self.tr('Файл не сохранён: {error}', error=self.error_text(result.save_error)),
                )
            return (
                self.tr('Скопировано в буфер'),
                self.tr('Файл не сохранялся. Вставьте Ctrl+V в Telegram, письмо или чат.'),
            )
        if not result.clipboard_enabled and result.path is not None:
            return (
                self.tr('Сохранено'),
                self.tr('Копирование в буфер выключено. Файл: {file}', file=result.path.name),
            )
        if result.clipboard_enabled and not result.clipboard_ok and result.path is not None:
            return (
                self.tr('Файл сохранён'),
                self.tr('Буфер недоступен: {detail}. Файл: {file}', detail=self.error_text(result.clipboard_error), file=result.path.name),
            )
        if not result.clipboard_enabled and result.path is None:
            return (
                self.tr('Снимок не сохранён'),
                self.tr('Копирование в буфер и сохранение в папку выключены. Включите хотя бы одно в настройках.'),
            )
        return (
            self.tr('Не удалось сохранить'),
            self.error_text(result.clipboard_error or result.save_error),
        )

    def repeat_last(self) -> None:
        if self._quitting or self.overlay.active:
            return
        if not self.last_rect:
            self.toast(self.tr('Повтор недоступен'), self.tr('Сначала сделайте хотя бы один снимок.'))
            return
        try:
            image = self.grab_screen()
            x1, y1, x2, y2 = self.last_rect
            x1 = max(0, min(image.width, x1))
            y1 = max(0, min(image.height, y1))
            x2 = max(0, min(image.width, x2))
            y2 = max(0, min(image.height, y2))
            if x2 - x1 < 2 or y2 - y1 < 2:
                self.toast(self.tr('Область недоступна'), self.tr('Конфигурация мониторов изменилась. Выделите область заново.'))
                return
            crop = image.crop((x1, y1, x2, y2))
            point = (
                virtual_screen_rect().left + (x1 + x2) // 2,
                virtual_screen_rect().top + (y1 + y2) // 2,
            )
            self._deliver(crop, point)
        except Exception as exc:
            log.exception("Repeat capture failed")
            self.toast(self.tr('Ошибка'), self.error_text(exc))

    def capture_fullscreen(self) -> None:
        if self._quitting or self.overlay.active:
            return
        try:
            image = self.grab_screen()
            point = (virtual_screen_rect().left + image.width // 2, virtual_screen_rect().top + image.height // 2)
            self._deliver(image, point)
        except Exception as exc:
            log.exception("Fullscreen capture failed")
            self.toast(self.tr('Ошибка'), self.error_text(exc))

    # ------------------------------------------------------------- settings

    def open_history_item(self, index: int) -> None:
        item = self.history.get(index)
        if item is None:
            self.toast(self.tr('Снимок недоступен'), self.tr('Он больше не находится в истории.'))
            return
        try:
            image = item.image()
            self.copy_image_to_clipboard(image)
            if item.path is not None and item.path.is_file():
                self.open_path(item.path)
            else:
                self.show_preview(image, None)
        except Exception as exc:
            log.exception("Could not open screenshot from tray history")
            self.toast(self.tr('Не удалось открыть снимок'), self.error_text(exc))

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
        if not self.can_share:
            self.close_share()
        language = resolve_language(self.settings.advanced.language)
        if language != self._language:
            self._language = language
            if self.toasts.current is not None:
                self.toasts.current.close()
            for child in self.root.winfo_children():
                if isinstance(child, tk.Toplevel):
                    child.event_generate("<<AreaGrabLanguageChanged>>", when="tail")
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
                self.tr('Горячая клавиша недоступна'),
                self.tr('{shortcut}: {error}. Выберите другое сочетание в настройках.', shortcut=target, error=self.error_text(exc)),
            )

    def pause_hotkeys(self) -> None:
        self._applied_hotkey = self.hotkeys.last_hotkey or self.settings.hotkeys.capture
        self.hotkeys.pause()
        self.tray.refresh()

    def resume_hotkeys(self) -> None:
        try:
            self.hotkeys.resume(self._applied_hotkey or self.settings.hotkeys.capture)
        except HotkeyError as exc:
            log.exception("Could not resume the hotkey")
            self.toast(self.tr('Горячая клавиша недоступна'), self.error_text(exc))
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
            self.toast(self.tr('AreaGrab снова работает'), self.tr('Горячие клавиши включены.'), duration_override=1800)
        else:
            self.pause_hotkeys()
            self.toast(self.tr('Работа AreaGrab приостановлена'), self.tr('Горячие клавиши отключены. Возобновить можно через меню.'), duration_override=1800)

    def _save_capture_stats(self) -> None:
        self._capture_stats_after = None
        self.save_settings()

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
            title=self.tr('Выберите папку для снимков'),
        )
        return selected or None

    def open_folder(self) -> None:
        try:
            folder = storage.target_folder(self.settings)
            storage.ensure_folder(folder)
            open_path(folder)
        except Exception as exc:
            log.exception("Could not open the screenshot folder")
            self.toast(self.tr('Не удалось открыть папку'), self.error_text(exc))

    def open_logs(self) -> None:
        try:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            open_path(LOG_DIR)
        except Exception as exc:
            log.exception("Could not open the log folder")
            self.toast(self.tr('Не удалось открыть логи'), self.error_text(exc))

    def reset_settings(self) -> None:
        previous = self.settings
        self.settings = Settings.default()
        self.settings.pro_preview = previous.pro_preview
        self.settings.license = previous.license
        self.settings.advanced.first_run_done = True
        self._applied_hotkey = None
        self.settings_changed()
        self.toast(self.tr('Настройки сброшены'), self.tr('Значения по умолчанию применены.'))

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
            self.toast(self.tr('Скопировано'), self.tr('Снимок снова в буфере. Ctrl+V.'))
        except Exception as exc:
            log.exception("Recopy failed")
            self.toast(self.tr('Не удалось скопировать'), self.error_text(exc))

    def copy_image_to_clipboard(self, image: Image.Image) -> bool:
        try:
            clipboard_service.copy_image(image)
            self.toast(self.tr('Скопировано'), self.tr('Снимок в буфере. Ctrl+V.'))
            return True
        except Exception as exc:
            log.exception("Clipboard copy failed")
            self.toast(self.tr('Не удалось скопировать'), self.error_text(exc))
            return False

    def open_share(self, source: ShareSource) -> None:
        if self.can_share:
            from .ui.share_window import ShareWindow

            self.close_share()
            self._share_window = ShareWindow(self, source)

    def close_share(self) -> None:
        if self._share_window is not None and self._share_window.winfo_exists():
            self._share_window.destroy()
        self._share_window = None

    def open_pro(self, image: Image.Image | None = None) -> None:
        show_plans(self, image if image is not None else self.last_image)

    def open_editor(self, image: Image.Image) -> None:
        if self.settings.pro_preview.remaining:
            EditorWindow(self, image)
        else:
            self.open_pro()

    def record_editor_export(self) -> None:
        self.settings.pro_preview.exports += 1
        self.save_settings()
        for window in self.root.winfo_children():
            if isinstance(window, tk.Toplevel):
                window.event_generate("<<AreaGrabTrialChanged>>", when="tail")

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
        """Open a compact, readable About window from the tray."""
        existing = getattr(self, "_about_window", None)
        if existing is not None:
            try:
                if existing.winfo_exists():
                    existing.lift()
                    existing.focus_force()
                    return
            except tk.TclError:
                pass
        window = tk.Toplevel(self.root)
        self._about_window = window
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", window.destroy)
        frame = ttk.Frame(window, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AreaGrab", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        version = ttk.Label(frame, foreground="#64748b")
        version.pack(anchor="w", pady=(0, 16))
        ttk.Label(
            frame,
            text='Быстрые скриншоты экрана для Windows.',
            font=("Segoe UI", 11),
        ).pack(anchor="w")
        ttk.Label(
            frame,
            text='Выделяйте область, сохраняйте снимки в JPG или PNG, копируйте в буфер обмена и просматривайте недавние снимки.',
            wraplength=405, justify="left",
        ).pack(anchor="w", pady=(8, 16))
        shortcuts = ttk.Label(frame, justify="left", wraplength=405)
        shortcuts.pack(anchor="w")
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(20, 0))
        ttk.Button(actions, text='Сайт программы', command=lambda: open_url(WEBSITE_URL)).pack(side="left")
        ttk.Button(actions, text='Закрыть', command=window.destroy).pack(side="right")
        labels = capture_labels(window)

        def refresh(_event=None):
            window.title(self.tr("О программе — AreaGrab"))
            version.configure(text=self.tr("Версия {version}", version=__version__))
            shortcut = self.settings.hotkeys.capture.replace("print_screen", "PrtScr")
            shortcuts.configure(text=self.tr(
                "Сделать снимок: {detail}\nПовторить область: Ctrl+PrtScr", detail=shortcut,
            ))
            update_labels(labels, self.tr)

        window.bind("<<AreaGrabLanguageChanged>>", refresh)
        refresh()
        window.lift()
        window.focus_force()

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
        self.close_share()
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
    parser.add_argument("--preview-pro", action="store_true", help="enable Pro features in the test build")
    parser.add_argument("--version", action="store_true", help="print version")
    return parser


def main(argv: list[str] | None = None) -> None:
    setup_logging()
    enable_dpi_awareness()
    args = build_parser().parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return

    is_primary = acquire_single_instance()
    root = tk.Tk()
    root.withdraw()
    try:
        if not is_primary:
            language = resolve_language(Settings.load().advanced.language)

            def tr(text):
                return translate(text, language)

            LocalizedDialog(
                root, APP_NAME,
                tr("AreaGrab уже запущен. Иконка приложения находится в системном трее."),
                tr,
            )
            return
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
