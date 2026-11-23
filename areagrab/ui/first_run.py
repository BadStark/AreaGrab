from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .. import __version__
from ..constants import APP_NAME
from ..storage import is_writable
from ..win32_utils import (
    is_snipping_tool_prtscr_enabled,
    set_snipping_tool_prtscr_enabled,
)

log = logging.getLogger(__name__)


class FirstRunWindow:
    def __init__(self, app) -> None:
        self.app = app
        self.top = tk.Toplevel(app.root)
        self.top.title(f"{APP_NAME} — первый запуск")
        self.top.geometry("620x520")
        self.top.resizable(False, False)
        self.top.protocol("WM_DELETE_WINDOW", self._finish)

        style = ttk.Style(self.top)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        pad = 24
        ttk.Label(
            self.top,
            text=f"{APP_NAME} {__version__}",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w", padx=pad, pady=(pad, 0))
        ttk.Label(
            self.top,
            text="Снимок → Ctrl+V. Без лишних окон.",
            font=("Segoe UI", 11),
            foreground="#334155",
        ).pack(anchor="w", padx=pad, pady=(2, 14))
        ttk.Label(
            self.top,
            text="Нажмите PrtScr, выделите область и отпустите мышь. "
            "Снимок сразу окажется в буфере обмена — его можно вставить в Telegram, письмо или чат.",
            wraplength=560,
        ).pack(anchor="w", padx=pad)

        box = ttk.LabelFrame(self.top, text="Настройки по умолчанию", padding=14)
        box.pack(fill="x", padx=pad, pady=16)

        self.var_save = tk.BooleanVar(value=app.settings.save.enabled)
        self.var_copy = tk.BooleanVar(value=app.settings.clipboard.copy_image)
        self.var_autostart = tk.BooleanVar(value=app.settings.advanced.autostart)

        ttk.Checkbutton(box, text="Сохранять снимки в папку", variable=self.var_save).pack(
            anchor="w", pady=3
        )
        ttk.Checkbutton(box, text="Копировать в буфер обмена", variable=self.var_copy).pack(
            anchor="w", pady=3
        )
        ttk.Checkbutton(
            box, text="Запускать при входе в Windows", variable=self.var_autostart
        ).pack(anchor="w", pady=3)

        folder_row = ttk.Frame(box)
        folder_row.pack(fill="x", pady=(10, 0))
        self.var_folder = tk.StringVar(value=app.settings.save.folder)
        ttk.Entry(folder_row, textvariable=self.var_folder).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(folder_row, text="Изменить…", command=self._browse).pack(
            side="left", padx=(8, 0)
        )

        self.snip_label = ttk.Label(self.top, text="")
        self.snip_label.pack(anchor="w", padx=pad, pady=(0, 4))
        self.snip_button = ttk.Button(
            self.top, text="Отключить PrtScr в Snipping Tool", command=self._fix_snipping
        )
        self.snip_button.pack(anchor="w", padx=pad)
        self._refresh_snipping()

        buttons = ttk.Frame(self.top)
        buttons.pack(fill="x", padx=pad, pady=20)
        ttk.Button(buttons, text="Попробовать сейчас", command=self._try_it).pack(
            side="left"
        )
        ttk.Button(buttons, text="Готово", command=self._finish).pack(
            side="right"
        )

    def _browse(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.top,
            initialdir=self.var_folder.get(),
            title="Выберите папку для снимков",
        )
        if selected:
            self.var_folder.set(selected)

    def _refresh_snipping(self) -> None:
        enabled = is_snipping_tool_prtscr_enabled()
        if enabled:
            self.snip_label.config(
                text="Windows 11 также открывает Snipping Tool по PrtScr. Обычно AreaGrab подавляет его, но можно отключить настройку Windows.",
                foreground="#b45309",
                wraplength=560,
            )
            self.snip_button.state(["!disabled"])
        else:
            self.snip_label.config(text="PrtScr свободен: Snipping Tool его не перехватывает.", foreground="#16a34a")
            self.snip_button.state(["disabled"])

    def _fix_snipping(self) -> None:
        if set_snipping_tool_prtscr_enabled(False):
            self._refresh_snipping()
        else:
            messagebox.showerror("Ошибка", "Не удалось изменить настройку Windows.", parent=self.top)

    def _apply(self) -> bool:
        folder = self.var_folder.get().strip()
        if self.var_save.get() and folder:
            ok, error = is_writable(Path(folder))
            if not ok:
                messagebox.showerror(
                    "Папка недоступна",
                    f"Не удалось писать в папку:\n{folder}\n\n{error}",
                    parent=self.top,
                )
                return False
        s = self.app.settings
        s.save.enabled = bool(self.var_save.get())
        s.save.folder = folder
        s.clipboard.copy_image = bool(self.var_copy.get())
        s.advanced.autostart = bool(self.var_autostart.get())
        s.advanced.first_run_done = True
        self.app.settings_changed()
        return True

    def _try_it(self) -> None:
        if not self._apply():
            return
        self.top.destroy()
        self.app.first_run_window = None
        self.app.request_capture()

    def _finish(self) -> None:
        if not self._apply():
            return
        self.top.destroy()
        self.app.first_run_window = None
