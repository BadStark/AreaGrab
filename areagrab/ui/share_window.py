"""The sharing window owns the lifetime of the active network session."""
from __future__ import annotations

import math
import queue
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

from PIL import Image, ImageTk

from ..constants import resource_path
from ..lan_adapters import find_adapters
from ..lan_share import SharedImage, ShareSession, qr_image
from ..share_source import ShareSource
from .localization import capture_labels, update_labels


class ShareWindow(tk.Toplevel):
    def __init__(self, app, source: ShareSource) -> None:
        super().__init__(app.root)
        self.app = app
        self.image = None
        self.adapters = []
        self.session: ShareSession | None = None
        self.logo = b""
        self.qr_photo = None
        self.status_key = "Подготовка передачи…"
        self.timer = None
        self.ready = queue.SimpleQueue()
        self.source: ShareSource | None = source
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _event: self.destroy())
        self.bind("<Destroy>", self._on_destroy)
        self.bind("<<AreaGrabLanguageChanged>>", self._translate)
        self.resizable(False, False)

        body = ttk.Frame(self, padding=20)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Подключите устройство к той же Wi-Fi сети и отсканируйте QR-код.",
                  wraplength=360, justify="center").pack(anchor="center")
        self.qr = ttk.Label(body, anchor="center")
        self.qr.pack(pady=12)
        self.clock = ttk.Label(body, font=("Segoe UI", 14, "bold"))
        self.clock.pack()
        self.status = ttk.Label(body, wraplength=360, justify="center")
        self.status.pack(pady=(6, 8))
        self.notice = ttk.Label(body, wraplength=360, justify="center")
        self.notice.pack(fill="x", pady=(0, 10))

        self.network = ttk.Frame(body)
        ttk.Label(self.network, text="Сетевой адаптер").pack(anchor="w")
        self.adapter_box = ttk.Combobox(self.network, state="readonly", width=38)
        self.adapter_box.pack(fill="x")
        self.adapter_box.bind("<<ComboboxSelected>>", lambda _event: self._renew())
        buttons = ttk.Frame(body)
        buttons.pack(fill="x", pady=(8, 0))
        self.copy_button = ttk.Button(buttons, text="Копировать ссылку", command=self._copy)
        self.copy_button.pack(fill="x", pady=(0, 5))
        self.renew_button = ttk.Button(buttons, text="Обновить QR-код", command=self._renew)
        self.renew_button.pack(fill="x", pady=(0, 5))
        ttk.Button(buttons, text="Закрыть", command=self.destroy).pack(fill="x")

        self.labels = capture_labels(self)
        self._translate()
        self._start_preparation()

    def _start_preparation(self) -> None:
        if self.source is None:
            return
        self.copy_button.configure(state="disabled")
        self.renew_button.configure(state="disabled")
        self._status("Подготовка передачи…")
        threading.Thread(
            target=self._prepare, args=(self.source,), name="lan-share-prepare", daemon=True,
        ).start()
        self.timer = self.after(100, self._poll_ready)

    def _prepare(self, source: ShareSource) -> None:
        try:
            image = SharedImage.load(source)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError):
            self.ready.put(("Снимок удалён или недоступен.", None))
            return
        try:
            adapters = find_adapters()
        except (OSError, ValueError, subprocess.SubprocessError):
            self.ready.put(("Не удалось определить локальную сеть. Проверьте подключение.", None))
            return
        if not adapters:
            self.ready.put(("Нет подключения к локальной сети.", None))
            return
        try:
            logo = resource_path("areagrab_v2.png").read_bytes()
        except OSError:
            logo = b""
        self.ready.put((None, (image, adapters, logo)))

    def _poll_ready(self) -> None:
        self.timer = None
        try:
            error, result = self.ready.get_nowait()
        except queue.Empty:
            self.timer = self.after(100, self._poll_ready)
            return
        if error:
            self._status(error)
            self.renew_button.configure(state="normal")
            return
        self.source = None
        self.image, self.adapters, self.logo = result
        self.adapter_box.configure(values=tuple(
            f"{adapter.name} ({adapter.address.ip})" for adapter in self.adapters
        ))
        self.adapter_box.current(0)
        if len(self.adapters) > 1:
            self.network.pack(fill="x", before=self.copy_button.master)
        self._renew()

    def _renew(self) -> None:
        if self.image is None:
            self._start_preparation()
            return
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        if self.session is not None:
            self.session.stop()
            self.session = None
        adapter = self.adapters[self.adapter_box.current()]
        self.qr.configure(image="")
        self.qr_photo = None
        self.clock.configure(text="")
        self.notice.configure(text=self.app.tr(
            "Публичная сеть. Ссылка передаёт снимок без шифрования."
            if adapter.category == "Public" else "Передача по HTTP без шифрования."
        ))
        try:
            self.session = ShareSession(
                self.image, adapter, self.app.settings.lan_share.ttl,
                self.app.interface_language, self.logo,
            )
            self.qr_photo = ImageTk.PhotoImage(qr_image(self.session.url), master=self)
            self.qr.configure(image=self.qr_photo)
        except (OSError, RuntimeError, ImportError):
            if self.session is not None:
                self.session.stop()
                self.session = None
            self._status("Не удалось начать передачу. Проверьте подключение или выберите другой адаптер.")
            self._set_controls()
            return
        self._started = time.monotonic()
        self._status("Ожидаем подключение…")
        self._tick()

    def _tick(self) -> None:
        self.timer = None
        session = self.session
        seconds = math.ceil(session.remaining)
        minutes, seconds = divmod(seconds, 60)
        self.clock.configure(text=f"{minutes:02}:{seconds:02}")
        if session.expired or session.stopped.is_set():
            self.qr.configure(image="")
            self.qr_photo = None
            if session.delivered.is_set():
                self._status("Изображение передано.")
            else:
                self._status("Срок действия ссылки истёк. Обновите QR-код.")
            self._set_controls()
            return
        if session.delivered.is_set():
            self._status("Изображение передано.")
        elif time.monotonic() - self._started >= 15:
            self._status("Если страница не открывается, проверьте сеть, VPN, изоляцию устройств и брандмауэр Windows.")
        self._set_controls()
        self.timer = self.after(250, self._tick)

    def _set_controls(self) -> None:
        live = self.session is not None and not self.session.stopped.is_set() and not self.session.expired
        self.copy_button.configure(state="normal" if live else "disabled")
        self.renew_button.configure(state="normal" if self.adapters else "disabled")

    def _copy(self) -> None:
        if self.session is None or self.session.stopped.is_set() or self.session.expired:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.session.url)
        except tk.TclError:
            self._status("Не удалось скопировать ссылку.")
        else:
            self._status("Ссылка скопирована.")
            # Keep confirmation visible until a download or the next routing hint.
            self._started = time.monotonic()

    def _status(self, key) -> None:
        self.status_key = key
        self.status.configure(text=self.app.tr(key))

    def _translate(self, _event=None) -> None:
        self.title(self.app.tr("Отправить на устройство"))
        update_labels(self.labels, self.app.tr)
        self._status(self.status_key)
        if self.adapters:
            adapter = self.adapters[self.adapter_box.current()]
            self.notice.configure(text=self.app.tr(
                "Публичная сеть. Ссылка передаёт снимок без шифрования."
                if adapter.category == "Public" else "Передача по HTTP без шифрования."
            ))

    def _on_destroy(self, event) -> None:
        if event.widget is not self:
            return
        if self.timer is not None:
            self.after_cancel(self.timer)
            self.timer = None
        if self.session is not None:
            self.session.stop()
            self.session = None
        self.image = None
        self.source = None
        self.qr_photo = None
        if self.app._share_window is self:
            self.app._share_window = None
