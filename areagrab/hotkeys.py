from __future__ import annotations

import ctypes
import logging
import threading
import time
from ctypes import wintypes
from dataclasses import dataclass
from collections.abc import Callable

log = logging.getLogger(__name__)

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
HC_ACTION = 0
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012
LLKHF_INJECTED = 0x00000010

VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_ESCAPE = 0x1B
VK_SNAPSHOT = 0x2C


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


HOOKPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
)

user32.SetWindowsHookExW.argtypes = [
    ctypes.c_int,
    HOOKPROC,
    wintypes.HINSTANCE,
    wintypes.DWORD,
]
user32.SetWindowsHookExW.restype = ctypes.c_void_p
user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
user32.UnhookWindowsHookEx.restype = wintypes.BOOL
user32.CallNextHookEx.argtypes = [
    ctypes.c_void_p,
    ctypes.c_int,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.CallNextHookEx.restype = ctypes.c_ssize_t
user32.GetMessageW.argtypes = [
    ctypes.POINTER(wintypes.MSG),
    wintypes.HWND,
    wintypes.UINT,
    wintypes.UINT,
]
user32.GetMessageW.restype = wintypes.BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetCurrentThreadId.restype = wintypes.DWORD
user32.PostThreadMessageW.argtypes = [
    wintypes.DWORD,
    wintypes.UINT,
    wintypes.WPARAM,
    wintypes.LPARAM,
]
user32.PostThreadMessageW.restype = wintypes.BOOL


class HotkeyError(RuntimeError):
    pass


# Virtual-key map for the keys AreaGrab supports in the UI.
KEY_TO_VK: dict[str, int] = {
    "print_screen": VK_SNAPSHOT,
    "printscreen": VK_SNAPSHOT,
    "prtscr": VK_SNAPSHOT,
    "prtsc": VK_SNAPSHOT,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "page_up": 0x21,
    "page_down": 0x22,
    "space": 0x20,
    "spacebar": 0x20,
    "tab": 0x09,
    "esc": VK_ESCAPE,
    "escape": VK_ESCAPE,
    "enter": 0x0D,
    "return": 0x0D,
    "backspace": 0x08,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "minus": 0xBD,
    "-": 0xBD,
    "equals": 0xBB,
    "=": 0xBB,
    "plus": 0xBB,
    "[": 0xDB,
    "]": 0xDD,
    ";": 0xBA,
    "'": 0xDE,
    ",": 0xBC,
    ".": 0xBE,
    "/": 0xBF,
    "\\": 0xDC,
    "`": 0xC0,
}
for _ch in "abcdefghijklmnopqrstuvwxyz":
    KEY_TO_VK[_ch] = ord(_ch.upper())
for _digit in "0123456789":
    KEY_TO_VK[_digit] = ord(_digit)
for _n in range(1, 25):
    KEY_TO_VK[f"f{_n}"] = 0x6F + _n

VK_TO_KEY = {vk: key for key, vk in KEY_TO_VK.items()}
VK_TO_KEY[VK_SNAPSHOT] = "print_screen"
VK_TO_KEY[0xA0] = "shift"
VK_TO_KEY[0xA1] = "shift"
VK_TO_KEY[0xA2] = "ctrl"
VK_TO_KEY[0xA3] = "ctrl"
VK_TO_KEY[0xA4] = "alt"
VK_TO_KEY[0xA5] = "alt"

MODIFIER_VK = {
    0x10: "shift",
    0xA0: "shift",
    0xA1: "shift",
    0x11: "ctrl",
    0xA2: "ctrl",
    0xA3: "ctrl",
    0x12: "alt",
    0xA4: "alt",
    0xA5: "alt",
    0x5B: "win",
    0x5C: "win",
}


@dataclass(frozen=True)
class Binding:
    hotkey: str
    key_vk: int
    ctrl: bool = False
    alt: bool = False
    shift: bool = False
    win: bool = False


def _mod_state(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def _current_mods() -> tuple[bool, bool, bool, bool]:
    return (
        _mod_state(VK_CONTROL),
        _mod_state(VK_MENU),
        _mod_state(VK_SHIFT),
        _mod_state(VK_LWIN) or _mod_state(VK_RWIN),
    )


def parse_hotkey(text: str) -> Binding:
    raw = (text or "").strip().lower()
    if not raw:
        raise HotkeyError("empty hotkey")
    # Accept both "ctrl+shift+4" and "print_screen".
    parts = [p.strip() for p in raw.replace(" ", "_").split("+") if p.strip()]
    if len(parts) == 1 and parts[0] in ("print_screen", "printscreen", "prtscr"):
        parts = ["print_screen"]
    ctrl = alt = shift = win = False
    key: str | None = None
    for part in parts:
        if part in ("ctrl", "control", "left_ctrl", "right_ctrl"):
            ctrl = True
        elif part in ("alt", "menu", "left_alt", "right_alt"):
            alt = True
        elif part == "shift":
            shift = True
        elif part in ("win", "windows", "left_windows", "right_windows"):
            win = True
        else:
            key = part
    if key is None:
        raise HotkeyError("hotkey must contain a non-modifier key")
    key_vk = KEY_TO_VK.get(key)
    if key_vk is None:
        raise HotkeyError(f"unsupported key: {key}")

    mods = []
    if ctrl:
        mods.append("ctrl")
    if alt:
        mods.append("alt")
    if shift:
        mods.append("shift")
    if win:
        mods.append("win")
    mods.append("print_screen" if key_vk == VK_SNAPSHOT else key)
    return Binding(
        hotkey="+".join(mods),
        key_vk=key_vk,
        ctrl=ctrl,
        alt=alt,
        shift=shift,
        win=win,
    )


def validate_hotkey(text: str) -> bool:
    try:
        parse_hotkey(text)
        return True
    except HotkeyError:
        return False


def _key_name(vk: int) -> str:
    return VK_TO_KEY.get(vk, f"vk_{vk}")


class HotkeyManager:
    """Native WH_KEYBOARD_LL hotkey manager with a real Win32 message loop.

    The `keyboard` PyPI package's Windows listener exits its message loop on the
    first message (a long-standing bug), so AreaGrab uses its own hook. This also
    lets us suppress PrtScr reliably and record hotkeys without extra deps.
    """

    def __init__(self, callback: Callable[[], None], repeat_callback: Callable[[], None] | None = None) -> None:
        self._callback = callback
        self._repeat_callback = repeat_callback
        self._repeat_binding = parse_hotkey("ctrl+print_screen") if repeat_callback else None
        self._binding: Binding | None = None
        self._last_binding: Binding | None = None
        self._hook = None
        self._thread: threading.Thread | None = None
        self._thread_id: int = 0
        self._ready = threading.Event()
        self._start_error: str | None = None
        self._stop = False
        self._recording_cb: Callable[[str | None], None] | None = None
        self._last_trigger = 0.0
        self._paused = False
        self.ignore_injected = True
        self._mods: set[str] = set()

    def _sync_mods_from_async(self) -> None:
        ctrl, alt, shift, win = _current_mods()
        self._mods = {
            name
            for name, active in (
                ("ctrl", ctrl),
                ("alt", alt),
                ("shift", shift),
                ("win", win),
            )
            if active
        }

    # ------------------------------------------------------------- public

    @property
    def hotkey(self) -> str | None:
        return self._binding.hotkey if self._binding else None

    @property
    def last_hotkey(self) -> str | None:
        return self._last_binding.hotkey if self._last_binding else None

    @property
    def paused(self) -> bool:
        return self._paused

    def register(self, hotkey: str) -> None:
        binding = parse_hotkey(hotkey)
        self._ensure_started()
        self._sync_mods_from_async()
        self._binding = binding
        self._last_binding = binding
        self._paused = False
        log.info("Registered hotkey %r", binding.hotkey)

    def unregister(self) -> None:
        self._binding = None

    def pause(self) -> None:
        self._binding = None
        self._paused = True

    def resume(self, hotkey: str | None = None) -> None:
        target = hotkey or (self._last_binding.hotkey if self._last_binding else "")
        if not target:
            raise HotkeyError("no hotkey to resume")
        self.register(target)

    def record(self, callback: Callable[[str | None], None]) -> None:
        self._ensure_started()
        self._sync_mods_from_async()
        self._recording_cb = callback

    def close(self) -> None:
        self._stop = True
        self._recording_cb = None
        self._binding = None
        if self._hook:
            try:
                user32.UnhookWindowsHookEx(self._hook)
            except Exception:
                pass
            self._hook = None
        if self._thread_id:
            try:
                user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        self._thread_id = 0

    # ------------------------------------------------------------ internals

    def _ensure_started(self) -> None:
        if self._start_error:
            raise HotkeyError(self._start_error)
        if self._thread and self._thread.is_alive():
            return
        self._ready.clear()
        self._start_error = None
        self._stop = False
        self._thread = threading.Thread(target=self._run, name="hotkey-hook", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=2.0):
            raise HotkeyError("keyboard hook did not start")
        if self._start_error:
            raise HotkeyError(self._start_error)

    def _run(self) -> None:
        self._thread_id = int(kernel32.GetCurrentThreadId())
        self._hook_proc = HOOKPROC(self._hook_callback)
        hmod = kernel32.GetModuleHandleW(None)
        self._hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_proc, hmod, 0)
        if not self._hook:
            self._start_error = f"SetWindowsHookEx failed: {ctypes.WinError()}"
            self._ready.set()
            return
        self._ready.set()
        log.info("Keyboard hook installed")

        msg = wintypes.MSG()
        try:
            while not self._stop:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            if self._hook:
                try:
                    user32.UnhookWindowsHookEx(self._hook)
                except Exception:
                    pass
                self._hook = None

    def _hook_callback(self, n_code, w_param, l_param):
        try:
            if n_code == HC_ACTION:
                info = ctypes.cast(l_param, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                vk = int(info.vkCode)
                injected = bool(info.flags & LLKHF_INJECTED) and self.ignore_injected
                is_down = w_param in (WM_KEYDOWN, WM_SYSKEYDOWN)
                is_up = w_param in (WM_KEYUP, WM_SYSKEYUP)

                mod_name = MODIFIER_VK.get(vk)
                if mod_name is not None and not injected:
                    if is_down:
                        self._mods.add(mod_name)
                    elif is_up:
                        self._mods.discard(mod_name)

                if is_down and not injected:
                    if self._recording_cb is not None:
                        return self._handle_recording(vk)

                    ctrl = "ctrl" in self._mods
                    alt = "alt" in self._mods
                    shift = "shift" in self._mods
                    win = "win" in self._mods
                    # Repeat is a distinct shortcut and must win over PrtScr.
                    # A paused hotkey manager disables both shortcuts.
                    candidates = (
                        (self._repeat_binding, self._repeat_callback),
                        (self._binding, self._callback),
                    )
                    if not self._paused:
                        for binding, callback in candidates:
                            if binding is None or callback is None or vk != binding.key_vk:
                                continue
                            if (
                                ctrl == binding.ctrl
                                and alt == binding.alt
                                and shift == binding.shift
                                and win == binding.win
                            ):
                                now = time.monotonic()
                                if now - self._last_trigger >= 0.25:
                                    self._last_trigger = now
                                    try:
                                        callback()
                                    except Exception:
                                        log.exception("Hotkey callback failed")
                                return 1
        except Exception:
            log.exception("Keyboard hook error")
        return user32.CallNextHookEx(None, n_code, w_param, l_param)

    def _handle_recording(self, vk: int) -> int:
        callback = self._recording_cb
        if callback is None:
            return 1
        if vk == VK_ESCAPE:
            self._recording_cb = None
            try:
                callback(None)
            except Exception:
                log.exception("Hotkey recorder callback failed")
            return 1
        if vk in MODIFIER_VK:
            return 1
        parts = []
        for name in ("ctrl", "alt", "shift", "win"):
            if name in self._mods:
                parts.append(name)
        parts.append(_key_name(vk))
        text = "+".join(parts)
        self._recording_cb = None
        try:
            callback(text)
        except Exception:
            log.exception("Hotkey recorder callback failed")
        return 1
