from __future__ import annotations

import ctypes
import io
import logging
import struct
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_TEXT = 1
CF_BITMAP = 2
CF_DIB = 8
CF_UNICODETEXT = 13
CF_HDROP = 15

GMEM_MOVEABLE = 0x0002

# Important on 64-bit Windows: without explicit signatures ctypes truncates handles.
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalFree.argtypes = [ctypes.c_void_p]
kernel32.GlobalFree.restype = ctypes.c_void_p

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wintypes.UINT


class ClipboardError(RuntimeError):
    pass


def _open_clipboard(retries: int = 10, delay: float = 0.02) -> bool:
    for _ in range(retries):
        if user32.OpenClipboard(None):
            return True
        time.sleep(delay)
    return False


def _alloc_bytes(data: bytes) -> int:
    handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
    if not handle:
        raise ClipboardError("GlobalAlloc failed")
    ptr = kernel32.GlobalLock(handle)
    if not ptr:
        kernel32.GlobalFree(handle)
        raise ClipboardError("GlobalLock failed")
    try:
        ctypes.memmove(ptr, data, len(data))
    finally:
        kernel32.GlobalUnlock(handle)
    return int(handle)


def _set_data(fmt: int, data: bytes) -> None:
    handle = _alloc_bytes(data)
    if not user32.SetClipboardData(fmt, handle):
        kernel32.GlobalFree(handle)
        raise ClipboardError(f"SetClipboardData({fmt}) failed")


def _dib_bytes(image: Image.Image) -> bytes:
    """Build a 24-bit bottom-up CF_DIB (BITMAPINFOHEADER + pixels)."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width <= 0 or height <= 0:
        raise ClipboardError("empty image")

    stride = width * 3
    padded = ((stride + 3) // 4) * 4
    # PIL raw encoder writes BGR rows top-down; DIB needs bottom-up.
    raw = rgb.tobytes("raw", "BGR", stride, 1)
    rows = []
    pad = b"\x00" * (padded - stride)
    for y in range(height):
        rows.append(raw[y * stride : (y + 1) * stride] + pad)
    pixels = b"".join(reversed(rows))

    header = struct.pack(
        "<IiiHHIIiiII",
        40,  # biSize
        width,  # biWidth
        height,  # biHeight (positive = bottom-up)
        1,  # biPlanes
        24,  # biBitCount
        0,  # BI_RGB
        len(pixels),  # biSizeImage
        0,
        0,
        0,
        0,
    )
    return header + pixels


def _png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, "PNG", compress_level=1)
    return buffer.getvalue()


def png_bytes(image: Image.Image) -> bytes:
    """Encode PNG bytes used for the clipboard and the in-memory history."""
    return _png_bytes(image)


def copy_image(image: Image.Image, png_bytes: bytes | None = None) -> None:
    """Copy an image to the Windows clipboard as CF_DIB and PNG.

    CF_DIB is first for maximum compatibility (Word, Outlook, Paint).
    The registered "PNG" format helps Chrome, Gmail, Slack and Telegram.
    """
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")
    dib = _dib_bytes(image)
    png = png_bytes if png_bytes else _png_bytes(image)
    png_format = int(user32.RegisterClipboardFormatW("PNG"))

    if not _open_clipboard():
        raise ClipboardError("clipboard is busy")
    try:
        if not user32.EmptyClipboard():
            raise ClipboardError("EmptyClipboard failed")
        _set_data(CF_DIB, dib)
        if png_format:
            try:
                _set_data(png_format, png)
            except ClipboardError:
                # DIB is already there; PNG is a compatibility bonus.
                log.warning("Could not set PNG clipboard format", exc_info=True)
    finally:
        user32.CloseClipboard()


def copy_text(text: str) -> None:
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not _open_clipboard():
        raise ClipboardError("clipboard is busy")
    try:
        if not user32.EmptyClipboard():
            raise ClipboardError("EmptyClipboard failed")
        _set_data(CF_UNICODETEXT, data)
    finally:
        user32.CloseClipboard()


def copy_files(paths: list[Path | str]) -> None:
    """Copy files so Explorer (and apps that accept files) can paste them."""
    files = [str(Path(p).resolve()) for p in paths]
    if not files:
        raise ClipboardError("no files")
    # DROPFILES: pFiles, pt.x, pt.y, fNC, fWide
    header = struct.pack("<Iiiii", 20, 0, 0, 0, 1)
    payload = header
    for file in files:
        payload += file.encode("utf-16-le") + b"\x00\x00"

    if not _open_clipboard():
        raise ClipboardError("clipboard is busy")
    try:
        if not user32.EmptyClipboard():
            raise ClipboardError("EmptyClipboard failed")
        _set_data(CF_HDROP, payload)
    finally:
        user32.CloseClipboard()


def clear() -> None:
    if not _open_clipboard():
        raise ClipboardError("clipboard is busy")
    try:
        user32.EmptyClipboard()
    finally:
        user32.CloseClipboard()
