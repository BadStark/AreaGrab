from __future__ import annotations

import ctypes
import os
import sys
import winreg
from ctypes import wintypes
from dataclasses import dataclass
from pathlib import Path

from .constants import APP_NAME, MUTEX_NAME

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# ---------------------------------------------------------------- DPI

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4


def enable_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness before any Tk window is created."""
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
        user32.SetProcessDpiAwarenessContext.restype = wintypes.BOOL
        user32.SetProcessDpiAwarenessContext(
            ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
        )
        return
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        return
    except Exception:
        pass
    try:
        user32.SetProcessDPIAware()
    except Exception:
        pass


# ---------------------------------------------------------------- screen geometry

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    def as_tuple(self) -> tuple[int, int, int, int]:
        return self.left, self.top, self.right, self.bottom

    def contains_point(self, x: int, y: int) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom


def virtual_screen_rect() -> Rect:
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
    width = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    height = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    if width <= 0 or height <= 0:
        width, height = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        left = top = 0
    return Rect(left, top, left + width, top + height)


def work_area_for_point(x: int, y: int) -> Rect:
    """Return the work area (screen minus taskbar) of the monitor containing the point."""
    try:
        MONITOR_DEFAULTTONEAREST = 2

        class POINT(ctypes.Structure):
            _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", wintypes.LONG),
                ("top", wintypes.LONG),
                ("right", wintypes.LONG),
                ("bottom", wintypes.LONG),
            ]

        class MONITORINFO(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("rcMonitor", RECT),
                ("rcWork", RECT),
                ("dwFlags", wintypes.DWORD),
            ]

        user32.MonitorFromPoint.argtypes = [POINT, wintypes.DWORD]
        user32.MonitorFromPoint.restype = ctypes.c_void_p
        user32.GetMonitorInfoW.argtypes = [ctypes.c_void_p, ctypes.POINTER(MONITORINFO)]
        user32.GetMonitorInfoW.restype = wintypes.BOOL

        monitor = user32.MonitorFromPoint(POINT(x, y), MONITOR_DEFAULTTONEAREST)
        info = MONITORINFO()
        info.cbSize = ctypes.sizeof(MONITORINFO)
        if monitor and user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
            r = info.rcWork
            return Rect(r.left, r.top, r.right, r.bottom)
    except Exception:
        pass
    return virtual_screen_rect()


def is_fullscreen_foreground() -> bool:
    """True when the foreground window covers its monitor (games, video, presentations)."""
    try:
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetShellWindow.restype = wintypes.HWND
        user32.GetDesktopWindow.restype = wintypes.HWND
        user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        user32.GetWindowRect.restype = wintypes.BOOL

        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return False
        shell = user32.GetShellWindow()
        desktop = user32.GetDesktopWindow()
        if hwnd in (shell, desktop):
            return False
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return False
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        screen_w = user32.GetSystemMetrics(0)
        screen_h = user32.GetSystemMetrics(1)
        return width >= screen_w and height >= screen_h
    except Exception:
        return False


# ---------------------------------------------------------------- known folders

class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_ubyte * 8),
    ]


FOLDERID_Pictures = GUID(
    0x33E28130,
    0x4E1E,
    0x4676,
    (ctypes.c_ubyte * 8)(0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB),
)


def pictures_folder() -> Path:
    """Pictures known folder (respects OneDrive/redirected folders)."""
    try:
        shell32.SHGetKnownFolderPath.argtypes = [
            ctypes.POINTER(GUID),
            wintypes.DWORD,
            wintypes.HANDLE,
            ctypes.POINTER(ctypes.c_wchar_p),
        ]
        shell32.SHGetKnownFolderPath.restype = ctypes.c_long
        out = ctypes.c_wchar_p()
        hr = shell32.SHGetKnownFolderPath(
            ctypes.byref(FOLDERID_Pictures), 0, None, ctypes.byref(out)
        )
        if hr == 0 and out.value:
            path = Path(out.value)
            ctypes.windll.ole32.CoTaskMemFree(out)
            return path
    except Exception:
        pass
    return Path.home() / "Pictures"


def default_screenshots_folder() -> Path:
    return pictures_folder() / "Screenshots"


# ---------------------------------------------------------------- single instance

_mutex_handle = None


def acquire_single_instance() -> bool:
    """Create a named mutex. False means another instance is running."""
    global _mutex_handle
    try:
        kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel32.CreateMutexW.restype = wintypes.HANDLE
        handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
        if not handle:
            return True
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
        _mutex_handle = handle
        return True
    except Exception:
        return True


def show_message(title: str, text: str) -> None:
    try:
        user32.MessageBoxW.argtypes = [
            wintypes.HWND,
            wintypes.LPCWSTR,
            wintypes.LPCWSTR,
            wintypes.UINT,
        ]
        user32.MessageBoxW.restype = ctypes.c_int
        user32.MessageBoxW(None, text, title, 0x00000040)  # MB_ICONINFORMATION
    except Exception:
        pass


# ---------------------------------------------------------------- Snipping Tool / PrtScr

_SNIPPING_KEY = r"Control Panel\Keyboard"
_SNIPPING_VALUE = "PrintScreenKeyForSnippingEnabled"


def _windows_build() -> int:
    try:
        return sys.getwindowsversion().build
    except Exception:
        return 0


def is_snipping_tool_prtscr_enabled() -> bool:
    """Best-effort detection of the Windows 11 'PrtScr opens Snipping Tool' setting."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _SNIPPING_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _SNIPPING_VALUE)
            return int(value) != 0
    except FileNotFoundError:
        # Windows 11 enables it by default; Windows 10 uses the legacy clipboard behavior.
        return _windows_build() >= 22000
    except Exception:
        return False


def set_snipping_tool_prtscr_enabled(enabled: bool) -> bool:
    try:
        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, _SNIPPING_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.SetValueEx(key, _SNIPPING_VALUE, 0, winreg.REG_DWORD, 1 if enabled else 0)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- autostart

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE = APP_NAME


def autostart_command() -> str:
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        return f'"{exe}" --autostart'
    script = Path(__file__).resolve().parent.parent / "AreaGrab.py"
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    exe = pythonw if pythonw.exists() else Path(sys.executable)
    return f'"{exe}" "{script}" --autostart'


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as key:
            value, _ = winreg.QueryValueEx(key, _RUN_VALUE)
            return bool(value)
    except FileNotFoundError:
        return False
    except Exception:
        return False


def set_autostart(enabled: bool) -> bool:
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            if enabled:
                winreg.SetValueEx(key, _RUN_VALUE, 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, _RUN_VALUE)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False


# ---------------------------------------------------------------- shell

def open_path(path: str | os.PathLike) -> None:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
    except Exception:
        pass


def open_url(url: str) -> None:
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass


def reveal_in_explorer(path: str | os.PathLike) -> None:
    try:
        import subprocess

        subprocess.Popen(["explorer", "/select,", str(path)])
    except Exception:
        open_path(Path(path).parent)
