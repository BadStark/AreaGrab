# AreaGrab

Fast region screenshot tool for Windows. Press `PrtScr`, select an area, release — the image is already in your clipboard. Optionally save it to any folder; or turn saving off and keep the clipboard only.

**Current release:** 1.1.0 (free)  
**Next:** 1.2 Pro (annotations, pin, OCR, history, custom hotkeys, copy as file/path).

## What works in 1.1

- `PrtScr` global hotkey with a native Win32 low-level hook (no `keyboard` dependency, no admin).
- Automatic clipboard copy as `CF_DIB` + registered `PNG` format.
- Custom save folder, `Png`/`Jpg`, JPEG quality, filename template.
- “Save to folder” checkbox: when off, no file is written — clipboard and RAM history only.
- Settings window, first-run onboarding, tray menu with recent screenshots.
- Non-blocking toast with “Open”, “Folder”, “Repeat copy” actions.
- Per-monitor DPI awareness, virtual-screen multi-monitor capture.
- Repeat last region and full-screen capture.
- Per-user installer (no UAC), autostart, single instance.
- In-memory history of the last 10 screenshots.
- Logging and global exception hooks.
- Legal pages and proprietary EULA for 1.1+ (v1.0 remains MIT).

## Portable mode

If `portable.flag` is next to `AreaGrab.exe`, settings, logs and the default
screenshot folder are kept in `.\data` next to the exe. This is what the
`AreaGrab_1.1.0_portable.zip` build uses — no installer, admin rights, registry
or Start Menu writes. It is also the fallback when the Inno Setup installer
cannot create its temp folder.

## Run from source

```powershell
python -m pip install -r requirements.txt
python AreaGrab.py
```

Useful flags:

```powershell
python AreaGrab.py --version
python AreaGrab.py --settings
python AreaGrab.py --capture
python AreaGrab.py --reset
```

Settings live in `%APPDATA%\AreaGrab\settings.json`; logs in `%LOCALAPPDATA%\AreaGrab\logs`.

For testing without touching the real profile:

```powershell
$env:AREAGRAB_CONFIG_DIR="$PWD\.test-appdata"
$env:AREAGRAB_LOCAL_DIR="$PWD\.test-localappdata"
python AreaGrab.py
```

## Build

```powershell
python -m unittest discover -s tests -v
python -m PyInstaller --noconfirm --workpath build_v11 --distpath dist_final AreaGrab.spec
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' areagrab_setup.iss
```

Outputs:

- `dist_final\AreaGrab\AreaGrab.exe` — portable onedir build.
- `Output_v11\AreaGrab_Setup_1.1.0.exe` — per-user installer.

The installer and exe are currently unsigned. SmartScreen may show “Unknown publisher”. See `docs/IMPLEMENTATION.md` for the signing plan.

## Architecture

```
areagrab/
  app.py            # orchestration, event queue, delivery
  config.py         # JSON settings, defaults, migration
  clipboard.py      # CF_DIB + PNG via ctypes
  storage.py        # folder, names, atomic save
  history.py        # RAM history (PNG bytes + thumbnails)
  hotkeys.py        # native WH_KEYBOARD_LL hook + recorder
  win32_utils.py    # DPI, monitors, known folders, autostart, mutex
  ui/               # overlay, toast, settings, first run, tray, preview
tests/              # unittest suite
docs/PLAN.md        # product / UX / monetization plan
```

The Tk main thread only touches UI. Capture, clipboard and saving run in a worker; results come back through a `queue.Queue` polled by the main loop.

## License

AreaGrab 1.0 was released under the MIT License (preserved in `LICENSE-v1.0-MIT.txt`). AreaGrab 1.1 and later are distributed under the proprietary AreaGrab EULA (`LicenseAgreement.rtf`). Third-party components are listed in `THIRD_PARTY_NOTICES.txt`.
