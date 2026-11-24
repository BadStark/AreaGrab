from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__
from ..constants import APP_NAME, WEBSITE_URL
from ..hotkeys import validate_hotkey
from ..storage import target_folder
from ..win32_utils import (
    is_snipping_tool_prtscr_enabled,
    open_url,
    set_snipping_tool_prtscr_enabled,
)

log = logging.getLogger(__name__)


class SettingsWindow:
    def __init__(self, app) -> None:
        self.app = app
        self.root = app.root
        self.top = tk.Toplevel(self.root)
        self.top.title(f"{APP_NAME} — настройки")
        self.top.geometry("760x560")
        self.top.minsize(700, 500)
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self._recording = False
        self._loading = True

        style = ttk.Style(self.top)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        self.notebook = ttk.Notebook(self.top)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(12, 0))

        self._build_general()
        self._build_capture()
        self._build_saving()
        self._build_clipboard()
        self._build_notifications()
        self._build_about()

        bottom = ttk.Frame(self.top)
        bottom.pack(fill="x", padx=12, pady=10)
        self.saved_label = ttk.Label(bottom, text="", foreground="#16a34a")
        self.saved_label.pack(side="left")
        ttk.Button(bottom, text="Закрыть", command=self.close).pack(side="right")
        self.apply_button = ttk.Button(bottom, text="Применить", command=self._save)
        self.apply_button.pack(side="right", padx=(0, 10))

        self.top.after(50, self._load_values)
        for variable in (self.var_autostart, self.var_copy, self.var_clear_history,
                         self.var_hotkey, self.var_save_enabled, self.var_folder,
                         self.var_format, self.var_quality, self.var_template,
                         self.var_toast, self.var_duration, self.var_thumbnail):
            variable.trace_add("write", lambda *_args: self._mark_dirty())
        self.top.after(100, self._focus)

    def _focus(self) -> None:
        try:
            self.top.lift()
            self.top.focus_force()
        except tk.TclError:
            pass

    # ------------------------------------------------------------ helpers

    def _tab(self, title: str) -> ttk.Frame:
        frame = ttk.Frame(self.notebook, padding=16)
        self.notebook.add(frame, text=title)
        return frame

    @staticmethod
    def _row(parent: ttk.Frame, row: int, label: str) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))

    # ------------------------------------------------------------- build

    def _build_general(self) -> None:
        tab = self._tab("Общие")
        self.var_autostart = tk.BooleanVar()
        self.var_copy = tk.BooleanVar()
        self.var_clear_history = tk.BooleanVar()

        ttk.Checkbutton(
            tab,
            text="Запускать AreaGrab при входе в Windows",
            variable=self.var_autostart,
            command=self._mark_dirty,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            tab,
            text="Копировать снимок в буфер обмена",
            variable=self.var_copy,
            command=self._mark_dirty,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            tab,
            text="Очищать историю снимков при выходе",
            variable=self.var_clear_history,
            command=self._mark_dirty,
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

    def _build_capture(self) -> None:
        tab = self._tab("Захват")
        self.var_hotkey = tk.StringVar()
        self._row(tab, 0, "Горячая клавиша")
        hot_row = ttk.Frame(tab)
        hot_row.grid(row=0, column=1, sticky="ew", pady=6)
        self.hotkey_entry = ttk.Entry(hot_row, textvariable=self.var_hotkey, width=26)
        self.hotkey_entry.pack(side="left")
        self.record_button = ttk.Button(hot_row, text="Записать…", command=self._record_hotkey)
        self.record_button.pack(side="left", padx=(8, 0))

    def _build_saving(self) -> None:
        tab = self._tab("Сохранение")
        self.var_save_enabled = tk.BooleanVar()
        self.var_folder = tk.StringVar()
        self.var_format = tk.StringVar()
        self.var_quality = tk.IntVar()
        self.var_template = tk.StringVar()

        ttk.Checkbutton(
            tab,
            text="Сохранять снимки в папку",
            variable=self.var_save_enabled,
            command=self._mark_dirty,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        self._row(tab, 1, "Папка")
        folder_row = ttk.Frame(tab)
        folder_row.grid(row=1, column=1, sticky="ew", pady=3)
        ttk.Entry(folder_row, textvariable=self.var_folder, width=52).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(folder_row, text="Обзор…", command=self._browse).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(folder_row, text="Открыть", command=self.app.open_folder).pack(
            side="left", padx=(6, 0)
        )

        self._row(tab, 2, "Формат")
        self.format_box = ttk.Combobox(
            tab,
            textvariable=self.var_format,
            values=("JPG (меньше)", "PNG (чётче)"),
            state="readonly",
            width=18,
        )
        self.format_box.grid(row=2, column=1, sticky="w")
        self.format_box.bind("<<ComboboxSelected>>", lambda _e: self._mark_dirty())

        self._row(tab, 3, "Качество JPG")
        quality_row = ttk.Frame(tab)
        quality_row.grid(row=3, column=1, sticky="ew")
        quality_scale = ttk.Scale(
            quality_row,
            from_=50,
            to=100,
            variable=self.var_quality,
            command=lambda _v: self._quality_label(),
            length=220,
        )
        quality_scale.pack(side="left")
        quality_scale.bind("<ButtonRelease-1>", lambda _e: self._mark_dirty())
        self.quality_label = ttk.Label(quality_row, text="95")
        self.quality_label.pack(side="left", padx=(8, 0))

        self._row(tab, 4, "Шаблон имени")
        ttk.Entry(tab, textvariable=self.var_template, width=52).grid(
            row=4, column=1, sticky="ew"
        )
        ttk.Label(
            tab,
            text="Доступно: {date}, {time}, {datetime}. Расширение добавляется автоматически.",
            foreground="#64748b",
        ).grid(row=5, column=1, sticky="w", pady=(2, 8))

        ttk.Label(
            tab,
            text="Если галочка снята, снимок остаётся только в буфере и в истории (в памяти). Файл не создаётся.",
            foreground="#475569",
            wraplength=560,
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _build_clipboard(self) -> None:
        tab = self._tab("Буфер")
        ttk.Label(
            tab,
            text="Снимок автоматически копируется в буфер. Откройте Telegram, письмо или чат и нажмите Ctrl+V.",
            wraplength=560,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            tab,
            text="Windows хранит последние элементы в истории буфера (Win+V), если она включена в настройках системы.",
            wraplength=560,
            foreground="#475569",
        ).grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Label(
            tab,
            text="Если выключить копирование в разделе «Общие», снимок будет только сохраняться в папку. "
            "Для главного сценария AreaGrab оставьте копирование включённым.",
            wraplength=560,
            foreground="#64748b",
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Button(tab, text="Очистить историю снимков", command=self._clear_history).grid(
            row=3, column=0, sticky="w", pady=(18, 0)
        )

    def _build_notifications(self) -> None:
        tab = self._tab("Уведомления")
        self.var_toast = tk.BooleanVar()
        self.var_duration = tk.IntVar()
        self.var_thumbnail = tk.BooleanVar()

        ttk.Checkbutton(
            tab,
            text="Показывать уведомление после снимка",
            variable=self.var_toast,
            command=self._mark_dirty,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=4)
        ttk.Checkbutton(
            tab,
            text="Показывать миниатюру",
            variable=self.var_thumbnail,
            command=self._mark_dirty,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        self._row(tab, 2, "Длительность")
        duration = ttk.Combobox(
            tab,
            textvariable=self.var_duration,
            values=(1500, 2200, 3000, 4000, 6000),
            state="readonly",
            width=8,
        )
        duration.grid(row=2, column=1, sticky="w")
        duration.bind("<<ComboboxSelected>>", lambda _e: self._mark_dirty())
        ttk.Label(
            tab,
            text="По умолчанию 2,2 секунды. При наведении мыши уведомление остаётся открытым.",
            foreground="#64748b",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_about(self) -> None:
        tab = self._tab("О программе")
        ttk.Label(tab, text=f"{APP_NAME} {__version__}", font=("Segoe UI", 14, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            tab,
            text="Быстрый снимок области: PrtScr → выделили → Ctrl+V.",
            foreground="#475569",
        ).pack(anchor="w", pady=(4, 14))

        ttk.Button(tab, text="Открыть папку снимков", command=self.app.open_folder).pack(
            anchor="w", pady=3
        )
        ttk.Button(tab, text="Открыть папку логов", command=self.app.open_logs).pack(
            anchor="w", pady=3
        )
        ttk.Button(tab, text="Сайт AreaGrab", command=lambda: open_url(WEBSITE_URL)).pack(
            anchor="w", pady=3
        )
        ttk.Button(tab, text="Сбросить настройки", command=self._reset).pack(
            anchor="w", pady=(14, 3)
        )
        ttk.Label(
            tab,
            text="AreaGrab — быстрый захват экрана для Windows. Снимки можно сохранять в JPG/PNG, копировать в буфер и просматривать в истории. PrtScr — новая область; Ctrl+PrtScr — повтор последней области. История в памяти очищается при завершении приложения.",
            foreground="#64748b",
            wraplength=560,
        ).pack(anchor="w", pady=(14, 0))

    # ------------------------------------------------------------- values

    def _load_values(self) -> None:
        s = self.app.settings
        self.var_autostart.set(s.advanced.autostart)
        self.var_copy.set(s.clipboard.copy_image)
        self.var_clear_history.set(s.clipboard.clear_on_exit)
        self.var_hotkey.set(s.hotkeys.capture)
        self.var_save_enabled.set(s.save.enabled)
        self.var_folder.set(s.save.folder)
        self.var_format.set("PNG (чётче)" if s.save.format == "png" else "JPG (меньше)")
        self.var_quality.set(s.save.jpeg_quality)
        self.var_template.set(s.save.filename_template)
        self.var_toast.set(s.notifications.toast)
        self.var_duration.set(s.notifications.duration_ms)
        self.var_thumbnail.set(s.notifications.thumbnail)
        self._quality_label()
        self._baseline = self._snapshot()
        self._loading = False
        self._update_apply()

    def _quality_label(self) -> None:
        try:
            self.quality_label.config(text=str(int(self.var_quality.get())))
        except Exception:
            pass

    # ------------------------------------------------------------- actions

    def _snapshot(self) -> tuple:
        return (
            self.var_autostart.get(), self.var_copy.get(), self.var_clear_history.get(),
            self.var_hotkey.get().strip().lower(), self.var_save_enabled.get(),
            self.var_folder.get().strip(), self.var_format.get(), int(self.var_quality.get()),
            self.var_template.get(), self.var_toast.get(), int(self.var_duration.get()),
            self.var_thumbnail.get(),
        )

    def _update_apply(self) -> None:
        dirty = hasattr(self, "_baseline") and self._snapshot() != self._baseline
        self.apply_button.configure(state="normal" if dirty else "disabled")

    def _mark_dirty(self) -> None:
        if not self._loading:
            self._update_apply()

    def _save(self) -> bool:
        if self._recording:
            return False
        hotkey = self.var_hotkey.get().strip().lower()
        if hotkey and hotkey != self.app.settings.hotkeys.capture:
            if not validate_hotkey(hotkey):
                messagebox.showerror(
                    "Некорректная клавиша",
                    "Не удалось распознать сочетание. Примеры: print_screen, ctrl+shift+4.",
                    parent=self.top,
                )
                return False


        s = self.app.settings
        s.advanced.autostart = bool(self.var_autostart.get())
        s.clipboard.copy_image = bool(self.var_copy.get())
        s.clipboard.clear_on_exit = bool(self.var_clear_history.get())
        s.save.enabled = bool(self.var_save_enabled.get())
        s.save.folder = self.var_folder.get().strip()
        s.save.format = "png" if self.var_format.get().startswith("PNG") else "jpg"
        s.save.jpeg_quality = int(self.var_quality.get())
        s.save.filename_template = self.var_template.get().strip() or "AreaGrab_{date}_{time}"
        s.notifications.toast = bool(self.var_toast.get())
        s.notifications.duration_ms = int(self.var_duration.get())
        s.notifications.thumbnail = bool(self.var_thumbnail.get())

        if hotkey:
            s.hotkeys.capture = hotkey

        s.validate()
        self.app.settings_changed()
        self._baseline = self._snapshot()
        self._update_apply()
        self._flash_saved()
        return True

    def _flash_saved(self) -> None:
        self.saved_label.config(text="Сохранено")
        self.top.after(1500, lambda: self.saved_label.config(text=""))

    def _browse(self) -> None:
        initial = self.var_folder.get() or str(target_folder(self.app.settings))
        selected = filedialog.askdirectory(
            parent=self.top, initialdir=initial, title="Выберите папку для снимков"
        )
        if selected:
            self.var_folder.set(selected)
            self._mark_dirty()

    def _record_hotkey(self) -> None:
        if self._recording:
            return
        self._recording = True
        self.record_button.config(text="Нажмите сочетание…", state="disabled")
        try:
            self.app.record_hotkey(self._finish_record)
        except Exception as exc:
            self._recording = False
            self.record_button.config(text="Записать…", state="normal")
            messagebox.showerror("Ошибка", str(exc), parent=self.top)

    def _finish_record(self, key: str | None) -> None:
        if not self.top.winfo_exists():
            return
        self._recording = False
        self.record_button.config(text="Записать…", state="normal")
        self.app.resume_hotkeys()
        if key and key.lower() != "esc":
            self.var_hotkey.set(key.lower())
            self._mark_dirty()

    def _fix_snipping(self) -> None:
        if not is_snipping_tool_prtscr_enabled():
            self._refresh_snipping_status()
            return
        if not messagebox.askyesno(
            "Snipping Tool",
            "Отключить открытие Snipping Tool по PrtScr?\n\n"
            "Это меняет только вашу настройку Windows (HKCU), не требует прав администратора. "
            "AreaGrab продолжит работать по PrtScr.",
            parent=self.top,
        ):
            return
        if set_snipping_tool_prtscr_enabled(False):
            self._refresh_snipping_status()
            messagebox.showinfo(
                "Готово",
                "PrtScr больше не будет открывать Snipping Tool. "
                "Если изменение не применилось сразу — перезапустите Snipping Tool.",
                parent=self.top,
            )
        else:
            messagebox.showerror("Ошибка", "Не удалось изменить настройку Windows.", parent=self.top)

    def _refresh_snipping_status(self) -> None:
        enabled = is_snipping_tool_prtscr_enabled()
        if enabled:
            self.snip_status.config(
                text="Сейчас PrtScr также открывает Snipping Tool Windows.",
                foreground="#b45309",
            )
            self.snip_button.state(["!disabled"])
        else:
            self.snip_status.config(
                text="PrtScr не перехватывается Snipping Tool.", foreground="#16a34a"
            )
            self.snip_button.state(["disabled"])

    def _clear_history(self) -> None:
        self.app.clear_history()
        self._flash_saved()

    def _reset(self) -> None:
        if not messagebox.askyesno(
            "Сбросить настройки",
            "Вернуть все настройки AreaGrab к значениям по умолчанию?",
            parent=self.top,
        ):
            return
        self.app.reset_settings()
        self._load_values()

    def close(self) -> None:
        if self._recording:
            messagebox.showinfo(
                "Запись клавиши",
                "Нажмите сочетание клавиш или Esc, чтобы завершить запись.",
                parent=self.top,
            )
            return
        if hasattr(self, "_baseline") and self._snapshot() != self._baseline:
            choice = messagebox.askyesnocancel(
                "Несохранённые изменения",
                "Сохранить изменения настроек перед закрытием?\n\n"
                "Да — сохранить; Нет — закрыть без сохранения; Отмена — вернуться.",
                parent=self.top,
            )
            if choice is None:
                return
            if choice and not self._save():
                return
        self.top.destroy()
        self.app.settings_window = None
