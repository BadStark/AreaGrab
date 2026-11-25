from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

from PIL import Image, ImageTk

from ..editor import Mark, render
from .localization import capture_labels, update_labels

log = logging.getLogger(__name__)


def show_plans(app) -> None:
    existing = getattr(app, "_plans", None)
    if existing is not None and existing.winfo_exists():
        existing.lift()
        existing.focus_force()
        return
    window = app._plans = tk.Toplevel(app.root)
    window.resizable(False, False)
    body = ttk.Frame(window, padding=24)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="AreaGrab Pro", font=("Segoe UI", 20, "bold")).pack(anchor="w")
    ttk.Label(body, text="Редактор снимков", wraplength=360).pack(anchor="w", pady=(4, 16))
    plan = tk.StringVar(window, "year")
    for code, period, price in (("month", "В месяц", "$2.99 USD"), ("year", "В год", "$24.99 USD")):
        row = ttk.Frame(body)
        row.pack(fill="x", pady=4)
        ttk.Radiobutton(row, text=period, variable=plan, value=code).pack(side="left")
        ttk.Label(row, text=price).pack(side="right")
    ttk.Label(body, text="Оплата недоступна в тестовой версии.", wraplength=360).pack(
        anchor="w", pady=(16, 8)
    )
    offers = tk.BooleanVar(window, value=app.settings.pro_preview.show_offers)

    def save_preference():
        app.settings.pro_preview.show_offers = offers.get()
        app.save_settings()

    ttk.Checkbutton(body, text="Показывать предложения Pro", variable=offers,
                    command=save_preference).pack(anchor="w")
    ttk.Button(body, text="Закрыть", command=window.destroy).pack(anchor="e", pady=(16, 0))
    labels = capture_labels(window)

    def refresh(_event=None):
        window.title(app.tr("Планы Pro"))
        update_labels(labels, app.tr)

    window.bind("<<AreaGrabLanguageChanged>>", refresh)
    refresh()


class EditorWindow:
    def __init__(self, app, image: Image.Image) -> None:
        self.app = app
        self.image = image
        self.marks: list[Mark] = []
        self.undone: list[Mark] = []
        self.start = None
        self.viewport = (0, 0, 1, 1)
        self.top = tk.Toplevel(app.root)
        self.top.geometry("880x620")
        self.top.minsize(700, 420)

        tools = ttk.Frame(self.top, padding=8)
        tools.pack(fill="x")
        self.tool = tk.StringVar(self.top, "arrow")
        for index, (key, label) in enumerate((
            ("arrow", "Стрелка"), ("line", "Линия"), ("rectangle", "Прямоугольник"),
            ("highlight", "Маркер"), ("text", "Текст"), ("mask", "Скрыть область"),
        )):
            ttk.Radiobutton(tools, text=label, variable=self.tool, value=key).grid(
                row=index // 3, column=index % 3, sticky="w", padx=4, pady=2,
            )
        ttk.Button(tools, text="Отменить действие", command=self._undo).grid(row=0, column=3)
        ttk.Button(tools, text="Повторить действие", command=self._redo).grid(row=1, column=3)
        self.top.bind("<Control-z>", lambda _event: self._undo())
        self.top.bind("<Control-y>", lambda _event: self._redo())

        footer = ttk.Frame(self.top, padding=8)
        footer.pack(side="bottom", fill="x")
        self.status = ttk.Label(footer, wraplength=240)
        self.status.pack(side="left")
        ttk.Button(footer, text="Копировать", command=self._copy).pack(side="right")
        ttk.Button(footer, text="Сохранить копию", command=self._save).pack(side="right", padx=8)
        self.canvas = tk.Canvas(self.top, background="#0f172a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _event: self._draw())
        self.canvas.bind("<ButtonPress-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)

        self.labels = capture_labels(self.top)
        self.top.bind("<<AreaGrabLanguageChanged>>", self._refresh)
        self.top.bind("<<AreaGrabTrialChanged>>", self._refresh)
        self._refresh()

    def _refresh(self, _event=None) -> None:
        self.top.title(self.app.tr("Редактор снимков"))
        update_labels(self.labels, self.app.tr)
        self.status.configure(text=self.app.tr(
            "Пробных экспортов осталось: {count}", count=self.app.settings.pro_preview.remaining,
        ))

    def _draw(self, draft: Mark | None = None) -> None:
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        if width <= 1 or height <= 1:
            return
        marks = self.marks if draft is None else [*self.marks, draft]
        image = render(self.image, marks)
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        left, top = (width - image.width) // 2, (height - image.height) // 2
        self.viewport = (left, top, image.width, image.height)
        self.photo = ImageTk.PhotoImage(image, master=self.canvas)
        self.canvas.delete("all")
        self.canvas.create_image(left, top, image=self.photo, anchor="nw")

    def _point(self, event):
        left, top, width, height = self.viewport
        return (
            min(self.image.width - 1, max(0, (event.x - left) * self.image.width // width)),
            min(self.image.height - 1, max(0, (event.y - top) * self.image.height // height)),
        )

    def _press(self, event) -> None:
        left, top, width, height = self.viewport
        if left <= event.x < left + width and top <= event.y < top + height:
            self.start = self._point(event)

    def _drag(self, event) -> None:
        if self.start is not None and self.tool.get() != "text":
            self._draw(Mark(self.tool.get(), self.start, self._point(event), "#ed352f"))

    def _release(self, event) -> None:
        if self.start is None:
            return
        start, self.start = self.start, None
        tool = self.tool.get()
        end = self._point(event)
        text = ""
        if tool == "text":
            text = simpledialog.askstring(self.app.tr("Текст"), self.app.tr("Текст"), parent=self.top)
            if not text:
                return
        elif start == end:
            self._draw()
            return
        self.marks.append(Mark(tool, start, end, "#ed352f", text))
        self.undone.clear()
        self._draw()

    def _undo(self) -> None:
        if self.marks:
            self.undone.append(self.marks.pop())
            self._draw()

    def _redo(self) -> None:
        if self.undone:
            self.marks.append(self.undone.pop())
            self._draw()

    def _export_allowed(self) -> bool:
        if self.app.settings.pro_preview.remaining:
            return bool(self.marks)
        self.app.open_pro()
        return False

    def _copy(self) -> None:
        if self._export_allowed() and self.app.copy_image_to_clipboard(render(self.image, self.marks)):
            self.app.record_editor_export()

    def _save(self) -> None:
        if not self._export_allowed():
            return
        selected = filedialog.asksaveasfilename(
            parent=self.top, title=self.app.tr("Сохранить копию"),
            defaultextension=".png", filetypes=[("PNG", "*.png")],
        )
        if not selected or not self._export_allowed():
            return
        try:
            # Exclusive creation preserves every existing file, including the source screenshot.
            path = Path(selected)
            with path.open("xb") as output:
                try:
                    render(self.image, self.marks).save(output, format="PNG")
                except Exception:
                    output.close()
                    path.unlink(missing_ok=True)
                    raise
        except Exception as exc:
            log.exception("Could not save annotated screenshot")
            self.app.toast(self.app.tr("Не удалось сохранить"), self.app.error_text(exc))
            return
        self.app.record_editor_export()
        self.app.toast(self.app.tr("Сохранено"), str(path))
