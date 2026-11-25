"""Cooperative shutdown signal used by the Windows installer.

Only the current user's AreaGrab process listens. Installer requests exit,
and the application's normal quit path saves settings and removes hooks.
"""
from __future__ import annotations

import ctypes
import logging
import threading
from ctypes import wintypes

log = logging.getLogger(__name__)
EVENT_NAME = "Local\\AreaGrab_InstallerShutdown_v1"


def listen_for_installer_shutdown(on_shutdown) -> None:
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateEventW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateEventW.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    kernel.WaitForSingleObject.restype = wintypes.DWORD
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    handle = kernel.CreateEventW(None, False, False, EVENT_NAME)
    if not handle:
        log.warning("Installer shutdown event could not be created: %s", ctypes.get_last_error())
        return

    def wait() -> None:
        try:
            if kernel.WaitForSingleObject(handle, 0xFFFFFFFF) == 0:
                on_shutdown()
        except Exception:
            log.exception("Installer shutdown listener failed")
        finally:
            kernel.CloseHandle(handle)

    threading.Thread(target=wait, daemon=True, name="installer-shutdown").start()
