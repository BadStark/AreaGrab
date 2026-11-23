# Changelog

## 1.1.0 — 2026-11-13

### Added

- Automatic clipboard copy (`CF_DIB` + `PNG`) after every capture.
- Custom save folder with native folder picker.
- “Save to folder” checkbox; no file is written when disabled.
- Settings window (General, Capture, Saving, Clipboard, Notifications, About).
- First-run onboarding with a test capture and Snipping Tool check.
- Tray menu: capture, repeat region, full screen, recent screenshots, folder, settings, pause, about, exit.
- Non-blocking toast with file info and actions.
- Native `WH_KEYBOARD_LL` hotkey hook with `PrtScr` suppression and a hotkey recorder.
- Per-monitor DPI awareness (V2) and virtual-screen coordinates.
- Single-instance mutex and per-user autostart.
- In-memory history of the last 10 screenshots.
- PNG/JPG output, JPEG quality, filename template.
- Rotating logs and exception hooks.
- Per-user Inno Setup installer: no UAC, optional autostart, desktop shortcut.
- New multi-size icon and version resource.
- Unit tests for settings, storage, hotkeys, history and DIB encoding.
- New website (`Сайт/index.html`, `ru.html`), updated privacy/terms, proprietary EULA.
- Portable build (`AreaGrab_1.1.0_portable.zip`): `portable.flag` keeps settings,
  logs and the default screenshot folder in `.\data`, with no installer, UAC,
  registry or Start Menu writes.
- `Install-AreaGrab.cmd` launcher for environments where the installer cannot
  create its temp folder.

### Changed

- Build is now onedir (`dist_final\AreaGrab`) instead of onefile; UPX disabled.
- `AreaGrab.py` is a thin entry point over the `areagrab` package.
- Installer requires no administrator rights and installs to `%LOCALAPPDATA%\Programs\AreaGrab`.
- Saving happens atomically through a temporary file and `os.replace`.
- Default hotkey remains `PrtScr`; it can be changed in Settings.
- JPEG remains the default format for small files; PNG is available.

### Fixed

- `PrtScr` no longer has to fight Snipping Tool for the key while AreaGrab runs.
- Removed admin manifest from the executable.
- Windows 10/11 high-DPI coordinate mismatch.
- Tk calls from the keyboard thread (now a queue).
- Silent failures after capture (toast + log).
- Tray menu “recent screenshots” action signature.
- No single-instance guard.

### Known limitations

- UI is Russian-only in 1.1; English localization is planned.
- No annotations, pin, OCR, disk history, or licensing yet (Pro 1.2).
- Mixed-DPI multi-monitor setups need more hardware testing.
- Installer and exe are unsigned; SmartScreen may warn.
- `pystray` logs a harmless `ChangeWindowMessageFilterEx` warning on restricted tokens and continues.
