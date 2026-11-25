from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

from PIL import Image, ImageTk

from ..editor import Mark, render
from .localization import capture_labels, update_labels

log = logging.getLogger(__name__)


def show_plans(app, image: Image.Image | None) -> None:
    existing = getattr(app, "_plans", None)
    if existing is not None and existing.winfo_exists():
        existing.refresh(image)
        existing.lift()
        existing.focus_force()
        return
    app._plans = ProWindow(app, image)


class ProWindow(tk.Toplevel):
    def __init__(self, app, image: Image.Image | None) -> None:
        super().__init__(app.root)
        self.app = app
        self.image = image
        self.resizable(False, False)
        self.bind("<Escape>", lambda _event: self.destroy())

        navy, ink, mint = "#12263b", "#183049", "#a4efd3"
        hero = tk.Frame(self, background=navy, padx=24, pady=24)
        hero.pack(fill="x")
        tk.Label(hero, text="AreaGrab Pro", background=navy, foreground=mint,
                 font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
        tk.Label(hero, text="Редактируйте снимки без лимита", background=navy,
                 foreground="white", font=("Segoe UI", 23, "bold"),
                 wraplength=390, anchor="w", justify="left").pack(fill="x", pady=(6, 8))
        tk.Label(hero, text="Стрелки, текст, выделение и скрытие данных в одном редакторе.",
                 background=navy, foreground="#dde7f0", wraplength=390,
                 anchor="w", justify="left").pack(fill="x")

        body = ttk.Frame(self, padding=24)
        body.pack(fill="both", expand=True)
        plans = tk.Frame(body)
        plans.pack(fill="x")
        plans.columnconfigure((0, 1), weight=1, uniform="plan")
        for column, (period, price, detail, surface) in enumerate((
            ("В месяц", "$2.99 USD", "Списание каждый месяц", "#edf2f7"),
            ("В год", "$24.99 USD", "Экономия 30% за год", "#dff5ec"),
        )):
            card = tk.Frame(plans, background=surface, padx=14, pady=12)
            card.grid(row=0, column=column, sticky="nsew", padx=(0, 6) if not column else (6, 0))
            for label, size, weight in ((period, 10, "normal"), (price, 21, "bold"), (detail, 9, "normal")):
                tk.Label(card, text=label, foreground=ink, background=surface,
                         font=("Segoe UI", size, weight), wraplength=155,
                         justify="left", anchor="w").pack(fill="x")

        self.status = ttk.Label(body, wraplength=390, justify="left")
        self.status.pack(anchor="w", pady=(16, 8))
        self.try_editor = ttk.Button(body, text="Попробовать редактор снимков",
                                     command=self._try_editor, padding=(12, 7))
        self.try_editor.pack(anchor="w")
        ttk.Separator(body).pack(fill="x", pady=(16, 10))
        ttk.Label(body, text="Оплата недоступна в тестовой версии.", wraplength=390).pack(anchor="w")
        self.labels = capture_labels(self)
        self.bind("<<AreaGrabLanguageChanged>>", lambda _event: self.refresh(self.image))
        self.bind("<<AreaGrabTrialChanged>>", lambda _event: self.refresh(self.image))
        self.refresh(image)
        self.try_editor.focus_set()

    def refresh(self, image: Image.Image | None) -> None:
        self.image = image
        self.title(self.app.tr("Перейти на Pro"))
        update_labels(self.labels, self.app.tr)
        remaining = self.app.settings.pro_preview.remaining
        self.status.configure(text=self.app.tr("Пробных экспортов осталось: {count}", count=remaining))
        self.try_editor.state(["!disabled" if image is not None and remaining else "disabled"])
        if image is None and remaining:
            self.status.configure(text=self.app.tr("Сделайте снимок, чтобы попробовать редактор."))

    def _try_editor(self) -> None:
        if self.image is not None and self.app.settings.pro_preview.remaining:
            self.app.open_editor(self.image)
            self.destroy()

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
