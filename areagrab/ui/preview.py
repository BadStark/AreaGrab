from __future__ import annotations

import logging
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk

from PIL import Image, ImageTk

log = logging.getLogger(__name__)


class PreviewWindow:
    def __init__(self, app, image: Image.Image, path: Path | None = None) -> None:
        self.app = app
        self.image = image
        self.path = path
        self.top = tk.Toplevel(app.root)
        self.top.title("AreaGrab — предпросмотр")
        self.top.geometry("820x620")
        self.top.minsize(520, 420)

        self._photo: ImageTk.PhotoImage | None = None
        self.canvas = tk.Canvas(self.top, bg="#0f172a", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=10, pady=(10, 0))
        self.canvas.bind("<Configure>", lambda _e: self._render())

        bar = ttk.Frame(self.top)
        bar.pack(fill="x", padx=10, pady=10)
        ttk.Button(bar, text="Копировать", command=self._copy).pack(side="left")
        ttk.Button(bar, text="Сохранить как…", command=self._save_as).pack(
            side="left", padx=8
        )
        if path is not None:
            ttk.Button(
                bar, text="Открыть файл", command=lambda: app.open_path(path)
            ).pack(side="left")
        ttk.Button(bar, text="Закрыть", command=self.top.destroy).pack(side="right")

        self.top.after(50, self._render)

    def _render(self) -> None:
        if not self.canvas.winfo_exists():
            return
        width = max(100, self.canvas.winfo_width() - 4)
        height = max(100, self.canvas.winfo_height() - 4)
        image = self.image.copy()
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(image, master=self.canvas)
        self.canvas.delete("all")
        self.canvas.create_image(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            image=self._photo,
            anchor=tk.CENTER,
        )

    def _copy(self) -> None:
        self.app.copy_image_to_clipboard(self.image)

    def _save_as(self) -> None:
        selected = filedialog.asksaveasfilename(
            parent=self.top,
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")],
        )
        if not selected:
            return
        try:
            path = Path(selected)
            if path.suffix.lower() in (".jpg", ".jpeg"):
                self.image.convert("RGB").save(path, "JPEG", quality=95)
            else:
                self.image.save(path, "PNG")
            self.app.toast(
                "Сохранено", str(path), thumbnail=self.image, actions=[]
            )
        except Exception as exc:
            log.exception("Save as failed")
            self.app.toast("Ошибка", str(exc))
