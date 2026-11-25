"""Bound, short-lived HTTP transport for a single in-memory screenshot."""
from __future__ import annotations

import base64
import hmac
import io
import ipaddress
import os
import secrets
import socket
import threading
import time
from dataclasses import dataclass
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from socketserver import TCPServer

from PIL import Image

from .i18n import translate
from .lan_adapters import Adapter
from .share_source import ShareSource, file_identity


@dataclass(frozen=True)
class SharedImage:
    content: bytes
    width: int
    height: int
    extension: str

    @property
    def media_type(self) -> str:
        return "image/jpeg" if self.extension == "jpg" else "image/png"

    @classmethod
    def load(cls, source: ShareSource) -> SharedImage:
        if source.path is None:
            content = source.png
        else:
            with source.path.open("rb") as original:
                if source.identity != file_identity(os.fstat(original.fileno())):
                    raise ValueError("The screenshot file has changed")
                content = original.read()
                if source.identity != file_identity(os.fstat(original.fileno())):
                    raise ValueError("The screenshot file changed while being read")
        with Image.open(io.BytesIO(content), formats=("PNG", "JPEG")) as image:
            width, height = image.size
            extension = "jpg" if image.format == "JPEG" else "png"
            image.verify()
        return cls(content, width, height, extension)


def qr_image(url: str) -> Image.Image:
    import qrcode

    return qrcode.make(url, box_size=5, border=4).get_image().convert("RGB")


def _page(image: SharedImage, route: str, language: str, logo: bytes) -> bytes:
    def text(key: str) -> str:
        return escape(translate(key, language))

    brand = ""
    if logo:
        png = base64.b64encode(logo).decode("ascii")
        brand = f'<img width="34" height="34" alt="" src="data:image/png;base64,{png}">'
    length = f"{len(image.content):,}".replace(",", "\u202f")
    return f"""<!doctype html>
<html lang="{escape(language, quote=True)}"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>AreaGrab · {text('Снимок экрана')}</title>
<style>
*{{box-sizing:border-box}}body{{margin:0;background:#edf2f7;color:#12263b;
font:1rem/1.5 system-ui,sans-serif}}main{{max-width:64rem;margin:auto;padding:clamp(1rem,4vw,2rem)}}
header{{display:flex;align-items:center;gap:.625rem;font-weight:700}}
h1{{margin:.8rem 0 .25rem;font-size:clamp(1.5rem,4vw,2rem)}}p{{margin:.5rem 0 1rem}}
.preview{{display:block;width:auto;max-width:100%;height:auto;max-height:65vh;object-fit:contain;
background:white;border:1px solid #bbc9d7;border-radius:.6rem}}
.actions{{margin-top:1rem}}a{{display:inline-block;padding:.7rem 1rem;
background:#12263b;color:white;border-radius:.4rem;font-weight:650}}a:focus-visible{{outline:3px solid #126c51;outline-offset:3px}}
</style>
<main><header>{brand}<span>AreaGrab</span></header>
<h1>{text('Снимок экрана')}</h1>
<p dir="ltr">{image.width} × {image.height} px · {length} B</p>
<img class="preview" src="{route}/image" width="{image.width}" height="{image.height}"
 alt="{text('Снимок экрана')}">
<div class="actions"><a href="{route}/download" download="AreaGrab.{image.extension}">{text('Скачать снимок')}</a></div>
<p>{text('На iPhone можно нажать и удерживать снимок, чтобы сохранить его в Фото.')}</p>
</main></html>""".encode("utf-8")


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def log_message(self, _format, *_args):
        # Request lines and Referer headers can carry a live access token.
        pass

    def do_GET(self) -> None:
        self._get(send_body=True)

    def do_HEAD(self) -> None:
        self._get(send_body=False)

    def send_error(self, code, message=None, explain=None) -> None:
        if getattr(self, "request_version", "HTTP/0.9") == "HTTP/0.9":
            return
        if code == 501:
            code = 405
        body = self.server.unavailable
        self._headers(code, "text/plain; charset=utf-8", len(body))
        if getattr(self, "command", None) != "HEAD":
            self.wfile.write(body)

    def _headers(self, status: int, media_type: str, size: int, disposition: str = "") -> None:
        self.send_response_only(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(size))
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy",
                         "default-src 'none'; img-src 'self' data:; style-src 'unsafe-inline'; "
                         "frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        self.send_header("Connection", "close")
        if status == 405:
            self.send_header("Allow", "GET, HEAD")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()

    def _get(self, *, send_body: bool) -> None:
        session = self.server.session
        if self.request_version == "HTTP/0.9":
            return
        if self.headers.get_all("Host") != [session.authority]:
            self.send_error(400)
            return
        targets = self.requestline.split()
        if len(targets) != 3 or targets[1] != self.path or not self.path.isascii():
            self.send_error(404)
            return
        if session.expired or session.stopped.is_set():
            self.send_error(410)
            return
        if hmac.compare_digest(self.path, session.route):
            self._headers(200, "text/html; charset=utf-8", len(session.page))
            if send_body:
                self.wfile.write(session.page)
            return

        download = hmac.compare_digest(self.path, session.route + "/download")
        if not download and not hmac.compare_digest(self.path, session.route + "/image"):
            self.send_error(404)
            return
        image = session.image
        disposition = f'attachment; filename="AreaGrab.{image.extension}"' if download else ""
        self._headers(200, image.media_type, len(image.content), disposition)
        if send_body:
            content = memoryview(image.content)
            for start in range(0, len(content), 64 * 1024):
                if session.stopped.is_set() or session.expired:
                    return
                self.wfile.write(content[start:start + 64 * 1024])
            self.wfile.flush()
            if not session.stopped.is_set() and not session.expired:
                session.delivered.set()


class _Server(ThreadingHTTPServer):
    # Use a small, bounded pool of request threads. server_close waits for their exit.
    daemon_threads = False
    allow_reuse_address = False
    timeout = 0.1
    request_queue_size = 8

    def __init__(self, session: ShareSession, adapter: Adapter, language: str) -> None:
        self.session = session
        self.network = adapter.address.network
        self.unavailable = translate("Ссылка недоступна или устарела.", language).encode("utf-8")
        self._sockets: set[socket.socket] = set()
        self._lock = threading.Lock()
        super().__init__((str(adapter.address.ip), 0), _Handler)

    def server_bind(self) -> None:
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        # HTTPServer.server_bind uses getfqdn, which can do a DNS lookup.
        TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address

    def verify_request(self, request, client_address) -> bool:
        return (not self.session.stopped.is_set()
                and ipaddress.IPv4Address(client_address[0]) in self.network)

    def process_request(self, request, client_address) -> None:
        with self._lock:
            if self.session.stopped.is_set() or len(self._sockets) >= 8:
                self.shutdown_request(request)
                return
            request.settimeout(3)
            self._sockets.add(request)
        super().process_request(request, client_address)

    def process_request_thread(self, request, client_address) -> None:
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self._lock:
                self._sockets.discard(request)

    def handle_error(self, request, client_address) -> None:
        # Protocol and disconnect errors must not expose a request or its token.
        pass

    def interrupt(self) -> None:
        with self._lock:
            for connection in self._sockets:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


class ShareSession:
    """One adapter, one capability URL and one immutable image."""

    def __init__(self, image: SharedImage, adapter: Adapter, ttl: int, language: str,
                 logo: bytes = b"") -> None:
        self.image = image
        self.route = "/share/" + secrets.token_urlsafe(32)
        self.stopped = threading.Event()
        self.delivered = threading.Event()
        self._server = _Server(self, adapter, language)
        self.authority = f"{adapter.address.ip}:{self._server.server_port}"
        self.url = f"http://{self.authority}{self.route}"
        try:
            self.page = _page(image, self.route, language, logo)
            self.deadline = time.monotonic() + ttl
            self._thread = threading.Thread(target=self._serve, name="lan-share")
            self._thread.start()
        except BaseException:
            self._server.server_close()
            raise

    @property
    def remaining(self) -> float:
        return max(0.0, self.deadline - time.monotonic())

    @property
    def expired(self) -> bool:
        return time.monotonic() >= self.deadline

    def _serve(self) -> None:
        try:
            while not self.stopped.is_set() and not self.expired:
                self._server.handle_request()
        finally:
            self.stop()
            self._server.server_close()
            self._server.session = None

    def stop(self) -> None:
        self.stopped.set()
        self._server.interrupt()

    def wait_closed(self, timeout: float) -> bool:
        self._thread.join(timeout)
        return not self._thread.is_alive()
