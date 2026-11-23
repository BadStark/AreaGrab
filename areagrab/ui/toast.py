from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from ..win32_utils import work_area_for_point

log = logging.getLogger(__name__)

BG = "#0f172a"
FG = "#f8fafc"
MUTED = "#94a3b8"
ACCENT = "#22c55e"
BORDER = "#1e293b"


class Toast:
    def __init__(
        self,
        root: tk.Tk,
        title: str,
        message: str,
        thumbnail: Image.Image | None = None,
        actions: list[tuple[str, Callable[[], None]]] | None = None,
        duration_ms: int = 4000,
        point: tuple[int, int] | None = None,
    ) -> None:
        self.root = root
        self.duration_ms = duration_ms
        self._after_id: str | None = None
        self._closed = False

        self.top = tk.Toplevel(root)
        self.top.withdraw()
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        try:
            self.top.attributes("-alpha", 0.98)
        except tk.TclError:
            pass
        self.top.configure(bg=BORDER)

        outer = tk.Frame(self.top, bg=BG, padx=12, pady=10)
        outer.pack(fill="both", expand=True, padx=1, pady=1)

        content = tk.Frame(outer, bg=BG)
        content.pack(fill="both", expand=True)

        self._thumb_photo: ImageTk.PhotoImage | None = None
        if thumbnail is not None:
            thumb = thumbnail.copy()
            thumb.thumbnail((64, 64), Image.Resampling.LANCZOS)
            self._thumb_photo = ImageTk.PhotoImage(thumb, master=self.top)
            tk.Label(
                content,
                image=self._thumb_photo,
                bg=BG,
                bd=0,
                highlightthickness=0,
            ).pack(side="left", padx=(0, 10), anchor="n")

        text_frame = tk.Frame(content, bg=BG)
        text_frame.pack(side="left", fill="both", expand=True)

        tk.Label(
            text_frame,
            text=title,
            bg=BG,
            fg=FG,
            font=("Segoe UI", 10, "bold"),
            anchor="w",
            justify="left",
        ).pack(fill="x")

        tk.Label(
            text_frame,
            text=message,
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=290,
        ).pack(fill="x", pady=(2, 0))

        if actions:
            row = tk.Frame(text_frame, bg=BG)
            row.pack(fill="x", pady=(8, 0))
            for label, callback in actions:
                tk.Button(
                    row,
                    text=label,
                    command=lambda cb=callback: self._run(cb),
                    bg="#1e293b",
                    fg=FG,
                    activebackground="#334155",
                    activeforeground=FG,
                    relief="flat",
                    bd=0,
                    padx=8,
                    pady=3,
                    font=("Segoe UI", 9),
                    cursor="hand2",
                ).pack(side="left", padx=(0, 6))

        close = tk.Label(
            outer,
            text="×",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 12),
            cursor="hand2",
        )
        close.place(relx=1.0, rely=0.0, x=-8, y=2, anchor="ne")
        close.bind("<Button-1>", lambda _e: self.close())

        self.top.update_idletasks()
        width = max(320, self.top.winfo_reqwidth())
        height = max(86, self.top.winfo_reqheight())
        if point is None:
            point = (self.root.winfo_pointerx(), self.root.winfo_pointery())
        area = work_area_for_point(*point)
        x = area.right - width - 16
        y = area.bottom - height - 16
        x = max(area.left + 8, x)
        y = max(area.top + 8, y)
        self.top.geometry(f"{width}x{height}+{x}+{y}")

        self.top.bind("<Enter>", self._pause)
        self.top.bind("<Leave>", self._resume)
        self.top.deiconify()
        self.top.lift()
        self._schedule()

    def _schedule(self) -> None:
        self._after_id = self.top.after(self.duration_ms, self.close)

    def _pause(self, _event=None) -> None:
        if self._after_id:
            try:
                self.top.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _resume(self, _event=None) -> None:
        if not self._closed and self._after_id is None:
            self._schedule()

    def _run(self, callback: Callable[[], None]) -> None:
        self.close()
        try:
            callback()
        except Exception:
            log.exception("Toast action failed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        self._pause()
        try:
            self.top.destroy()
        except tk.TclError:
            pass


class ToastManager:
    def __init__(self, root: tk.Tk, enabled: bool = True, duration_ms: int = 4000) -> None:
        self.root = root
        self.enabled = enabled
        self.duration_ms = duration_ms
        self.current: Toast | None = None

    def configure(self, enabled: bool, duration_ms: int) -> None:
        self.enabled = enabled
        self.duration_ms = duration_ms

    def show(
        self,
        title: str,
        message: str,
        thumbnail: Image.Image | None = None,
        actions: list[tuple[str, Callable[[], None]]] | None = None,
        point: tuple[int, int] | None = None,
    ) -> Toast | None:
        if not self.enabled:
            return None
        if self.current is not None:
            self.current.close()
        try:
            self.current = Toast(
                self.root,
                title,
                message,
                thumbnail=thumbnail,
                actions=actions,
                duration_ms=self.duration_ms,
                point=point,
            )
            return self.current
        except Exception:
            log.exception("Could not show toast")
            return None
