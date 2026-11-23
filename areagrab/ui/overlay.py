from __future__ import annotations

import logging
import time
import tkinter as tk
from collections.abc import Callable

from PIL import Image, ImageTk

from ..win32_utils import virtual_screen_rect

log = logging.getLogger(__name__)


class SelectionOverlay:
    """Full-virtual-screen dimmed overlay with a bright selected rectangle."""

    def __init__(
        self,
        root: tk.Tk,
        on_done: Callable[[Image.Image, tuple[int, int, int, int]], None],
        on_cancel: Callable[[str], None],
    ) -> None:
        self.root = root
        self.on_done = on_done
        self.on_cancel = on_cancel
        self.top: tk.Toplevel | None = None
        self.canvas: tk.Canvas | None = None
        self.image: Image.Image | None = None
        self.dark_image: Image.Image | None = None
        self.dark_photo: ImageTk.PhotoImage | None = None
        self.sel_photo: ImageTk.PhotoImage | None = None
        self.sel_item: int | None = None
        self.border_item: int | None = None
        self.size_item: int | None = None
        self.hint_item: int | None = None
        self.start: tuple[int, int] | None = None
        self.current: tuple[int, int] | None = None
        self.active = False
        self._last_render = 0.0
        self._last_rect: tuple[int, int, int, int] | None = None
        self._dim = 0.4

    def set_dim(self, dim: float) -> None:
        self._dim = max(0.1, min(0.8, float(dim)))

    # ------------------------------------------------------------------ show

    def show(self, screenshot: Image.Image) -> None:
        if self.active:
            return
        self.image = screenshot.convert("RGB")
        img_w, img_h = self.image.size
        screen = virtual_screen_rect()
        # In a DPI-aware process these should match; if not, trust the image.
        origin_x, origin_y = screen.left, screen.top
        width, height = img_w, img_h
        self.dark_image = self.image.point(lambda p: int(p * self._dim))

        self.top = tk.Toplevel(self.root)
        self.top.withdraw()
        self.top.overrideredirect(True)
        self.top.geometry(f"{img_w}x{img_h}+{origin_x}+{origin_y}")
        self.top.attributes("-topmost", True)
        self.top.configure(cursor="crosshair", bg="black")
        self.top.protocol("WM_DELETE_WINDOW", lambda: self._cancel("window"))

        self.canvas = tk.Canvas(
            self.top,
            width=img_w,
            height=img_h,
            highlightthickness=0,
            bd=0,
            bg="black",
        )
        self.canvas.pack(fill="both", expand=True)

        self.dark_photo = ImageTk.PhotoImage(self.dark_image, master=self.canvas)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.dark_photo)

        self.hint_item = self.canvas.create_text(
            width // 2,
            28,
            text="Выделите область  ·  Esc / правый клик — отмена",
            fill="#f8fafc",
            font=("Segoe UI", 11),
            anchor=tk.N,
        )
        # Subtle background behind the hint.
        self.canvas.create_rectangle(
            width // 2 - 190,
            12,
            width // 2 + 190,
            46,
            fill="#0f172a",
            outline="",
            stipple="gray50",
        )
        self.canvas.tag_raise(self.hint_item)

        self.canvas.bind("<ButtonPress-1>", self._on_down)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<ButtonRelease-1>", self._on_up)
        self.canvas.bind("<Button-3>", lambda _e: self._cancel("right-click"))
        self.top.bind("<Escape>", lambda _e: self._cancel("escape"))

        self.active = True
        self.start = None
        self.current = None
        self._last_rect = None
        self._last_render = 0.0

        self.top.deiconify()
        self.top.lift()
        self.top.focus_force()
        # Tk may not deliver Escape until focus settles.
        self.top.after(10, self._focus)

    def _focus(self) -> None:
        if self.top is not None:
            try:
                self.top.focus_force()
            except tk.TclError:
                pass

    # ------------------------------------------------------------- selection

    def _on_down(self, event: tk.Event) -> None:
        self.start = (int(event.x), int(event.y))
        self.current = self.start
        self._clear_selection()

    def _on_move(self, event: tk.Event) -> None:
        if self.start is None:
            return
        self.current = (int(event.x), int(event.y))
        now = time.perf_counter()
        # ~30 fps is plenty for a selection rectangle and much cheaper at 4K.
        if now - self._last_render < 0.033:
            return
        self._last_render = now
        self._render_selection()

    def _on_up(self, event: tk.Event) -> None:
        if not self.active:
            return
        self.current = (int(event.x), int(event.y))
        self._render_selection()
        rect = self._rect()
        if rect is None or rect[2] - rect[0] < 8 or rect[3] - rect[1] < 8:
            self._cancel("too-small")
            return
        image = self.image
        self._close()
        if image is not None:
            self.on_done(image, rect)

    def _rect(self) -> tuple[int, int, int, int] | None:
        if self.start is None or self.current is None or self.image is None:
            return None
        sx, sy = self.start
        ex, ey = self.current
        if self.canvas is not None:
            # Clamp to the actual screenshot bounds.
            max_x = self.image.width
            max_y = self.image.height
            sx = max(0, min(max_x, sx))
            sy = max(0, min(max_y, sy))
            ex = max(0, min(max_x, ex))
            ey = max(0, min(max_y, ey))
        if ex < sx:
            sx, ex = ex, sx
        if ey < sy:
            sy, ey = ey, sy
        return int(sx), int(sy), int(ex), int(ey)

    def _render_selection(self) -> None:
        rect = self._rect()
        if rect is None or self.canvas is None or self.image is None:
            return
        x1, y1, x2, y2 = rect
        if x2 <= x1 or y2 <= y1:
            return
        if rect == self._last_rect:
            return
        self._last_rect = rect

        crop = self.image.crop(rect)
        self.sel_photo = ImageTk.PhotoImage(crop, master=self.canvas)
        if self.sel_item is None:
            self.sel_item = self.canvas.create_image(
                x1, y1, anchor=tk.NW, image=self.sel_photo
            )
        else:
            self.canvas.coords(self.sel_item, x1, y1)
            self.canvas.itemconfig(self.sel_item, image=self.sel_photo)

        if self.border_item is None:
            self.border_item = self.canvas.create_rectangle(
                x1, y1, x2, y2, outline="#22c55e", width=1
            )
        else:
            self.canvas.coords(self.border_item, x1, y1, x2, y2)

        label = f"{x2 - x1} × {y2 - y1}"
        tx = min(max(x2 + 8, 8), self.image.width - 120)
        ty = min(max(y2 + 8, 8), self.image.height - 28)
        if self.size_item is None:
            self.size_item = self.canvas.create_text(
                tx,
                ty,
                text=label,
                fill="#f8fafc",
                font=("Segoe UI", 10, "bold"),
                anchor=tk.NW,
            )
        else:
            self.canvas.coords(self.size_item, tx, ty)
            self.canvas.itemconfig(self.size_item, text=label)
        self.canvas.tag_raise(self.border_item)
        self.canvas.tag_raise(self.size_item)

    # ---------------------------------------------------------------- close

    def _clear_selection(self) -> None:
        if self.canvas is None:
            return
        for item in (self.sel_item, self.border_item, self.size_item):
            if item is not None:
                try:
                    self.canvas.delete(item)
                except tk.TclError:
                    pass
        self.sel_item = None
        self.border_item = None
        self.size_item = None
        self.sel_photo = None

    def _cancel(self, reason: str) -> None:
        if not self.active:
            return
        self._close()
        self.on_cancel(reason)

    def _close(self) -> None:
        self.active = False
        self._clear_selection()
        if self.top is not None:
            try:
                self.top.destroy()
            except tk.TclError:
                pass
        self.top = None
        self.canvas = None
        self.image = None
        self.dark_image = None
        self.dark_photo = None
        self.start = None
        self.current = None
        self._last_rect = None
