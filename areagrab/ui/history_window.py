"""Visual, paginated recent screenshot browser (RAM history only)."""
from __future__ import annotations

import logging
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk

log = logging.getLogger(__name__)
PAGE_SIZE = 8


class HistoryWindow:
    def __init__(self, app) -> None:
        self.app = app
        self.page = 0
        self.top = tk.Toplevel(app.root)
        self.top.title("AreaGrab — последние снимки")
        self.top.geometry("760x560")
        self.top.minsize(540, 400)
        self.top.protocol("WM_DELETE_WINDOW", self.close)
        self._photos: list[ImageTk.PhotoImage] = []

        header = ttk.Frame(self.top, padding=12)
        header.pack(fill="x")
        ttk.Label(header, text="Последние снимки", font=("Segoe UI", 13, "bold")).pack(anchor="w")
        ttk.Label(
            header,
            text="Нажмите на миниатюру: снимок скопируется в буфер и откроется. "
                 "Несохранённые снимки откроются в предпросмотре.",
            wraplength=690,
        ).pack(anchor="w", pady=(6, 0))

        self.gallery = ttk.Frame(self.top, padding=12)
        self.gallery.pack(fill="both", expand=True)
        footer = ttk.Frame(self.top, padding=12)
        footer.pack(fill="x")
        self.prev_button = ttk.Button(footer, text="← Новее", command=self.prev_page)
        self.prev_button.pack(side="left")
        self.page_label = ttk.Label(footer, text="")
        self.page_label.pack(side="left", padx=16)
        self.next_button = ttk.Button(footer, text="Старее →", command=self.next_page)
        self.next_button.pack(side="left")
        ttk.Button(footer, text="Закрыть", command=self.close).pack(side="right")
        self.render()

    def render(self) -> None:
        for child in self.gallery.winfo_children():
            child.destroy()
        self._photos.clear()
        items = self.app.history.items()
        pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
        self.page = min(self.page, pages - 1)
        visible = items[self.page * PAGE_SIZE:(self.page + 1) * PAGE_SIZE]
        for col in range(4):
            self.gallery.columnconfigure(col, weight=1, uniform="thumb")
        for offset, item in enumerate(visible):
            index = self.page * PAGE_SIZE + offset
            cell = ttk.Frame(self.gallery, padding=7)
            cell.grid(row=offset // 4, column=offset % 4, sticky="nsew")
            self.gallery.rowconfigure(offset // 4, weight=1)
            photo = ImageTk.PhotoImage(item.thumbnail.copy(), master=self.top)
            self._photos.append(photo)
            btn = ttk.Button(cell, image=photo, command=lambda i=index: self.open_item(i))
            btn.pack(expand=True, pady=(4, 6))
            ttk.Label(cell, text=item.timestamp.strftime("%d.%m %H:%M:%S")).pack()
            ttk.Label(cell, text=f"{item.width}×{item.height}").pack()
            ttk.Label(cell, text="Файл" if item.path else "В памяти").pack()
        self.page_label.configure(text=f"Страница {self.page + 1} из {pages} · {len(items)} снимков")
        self.prev_button.configure(state="normal" if self.page else "disabled")
        self.next_button.configure(state="normal" if self.page + 1 < pages else "disabled")

    def open_item(self, index: int) -> None:
        item = self.app.history.get(index)
        if item is None:
            self.render()
            return
        try:
            image = item.image()
            self.app.copy_image_to_clipboard(image)
            if item.path is not None and item.path.is_file():
                self.app.open_path(item.path)
            else:
                self.app.show_preview(image, None)
        except Exception as exc:
            log.exception("Could not open history item")
            self.app.toast("Не удалось открыть снимок", str(exc))

    def prev_page(self) -> None:
        if self.page > 0:
            self.page -= 1
            self.render()

    def next_page(self) -> None:
        if (self.page + 1) * PAGE_SIZE < len(self.app.history):
            self.page += 1
            self.render()

    def close(self) -> None:
        self.top.destroy()
        if getattr(self.app, "history_window", None) is self:
            self.app.history_window = None
