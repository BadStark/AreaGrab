# AreaGrab 1.1 — implementation status

**Date:** 13.11.2026  
**Version:** 1.1.0  
**Status:** built and tested locally; unsigned; Pro 1.2 not started.

## Done in 1.1

| Area | Status | Notes |
|---|---|---|
| Clipboard copy | ✅ | `CF_DIB` + registered `PNG`; verified with `ImageGrab.grabclipboard()` and a live drag test. |
| Save folder | ✅ | Native folder picker, Known Folder `Pictures`, writability probe. |
| Save toggle | ✅ | `save.enabled=False` creates no file; clipboard + RAM history still work. |
| Formats | ✅ | JPG (quality 50–100) and PNG; atomic write. |
| Settings | ✅ | JSON in `%APPDATA%\AreaGrab\settings.json`; schema/validation; reset. |
| First run | ✅ | Folder, save/clipboard/autostart options, Snipping Tool fix, test capture. |
| Tray | ✅ | Capture, repeat, full screen, recent 5, folder, settings, pause, about, exit. |
| Toast | ✅ | Non-modal, thumbnail, open/folder/retry actions, auto-hide. |
| Hotkey | ✅ | Native `WH_KEYBOARD_LL` hook; `PrtScr` suppression; recorder; no admin. |
| DPI | ✅ | Per-monitor V2 before Tk; virtual screen; tested at 3840×1080. |
| Single instance | ✅ | Named mutex. |
| Autostart | ✅ | HKCU Run; installer task optional. |
| History | ✅ | Last 10 in RAM, PNG bytes + thumbnails; no disk. |
| Repeat/fullscreen | ✅ | Tray actions. |
| Logging | ✅ | Rotating log in `%LOCALAPPDATA%\AreaGrab\logs`; excepthooks. |
| Installer | ✅ | Inno Setup, per-user, no UAC, optional autostart, uninstall. Built; clean-VM test pending. |
| Portable mode | ✅ | `portable.flag` keeps settings/logs/screenshots in `.\data`; ZIP needs no installer, UAC, registry or Start Menu. |
| Icon/version | ✅ | Multi-size ICO and version resource. |
| Tests | ✅ | 20 unittest cases. |
| Website/legal | ✅ | New EN/RU pages, privacy/terms, EULA; v1.0 MIT legacy noted. |

## Verified locally

- `python -m unittest discover -s tests -v` — 20 tests OK.
- Clipboard round-trip: 320×200 image → `ImageGrab.grabclipboard()` returns DIB 320×200.
- Live E2E: `PrtScr` → overlay → drag 300×200 → saved PNG 300×200, clipboard 300×200, history 1.
- Save-disabled E2E: no files, clipboard 190×140, history 1.
- Native hook: `print_screen` callback triggers; synthetic `ctrl+shift+9` callback; recorder returns `ctrl+shift+4`.
- DPI awareness: `GetProcessDpiAwareness` = 2 (per-monitor).
- Built exe starts, installs hook, logs, and stays in tray (pystray UIPI warning tolerated).
- Installer compiled: `Output_v11\AreaGrab_Setup_1.1.0.exe` (15.0 MB).
  SHA-256: `DCF8BC4447D1B3AAA7A3A8827A3FB42D28B5FDC3E02EF4224C62DC7B13832CF5`.
- Portable ZIP: `Output_v11\AreaGrab_1.1.0_portable.zip` (19.6 MB).
  SHA-256: `81C7C4CFF3A6668AE1C6F59227600D64C03EED2F7A1DA0F473C7009D03F279B4`.
- Site copies: `Сайт/downloads/AreaGrab_Setup_1.1.0.exe`,
  `Сайт/downloads/AreaGrab_1.1.0_portable.zip`,
  `Сайт/downloads/Install-AreaGrab.cmd` (same hashes).
- Portable mode verified: extracting the ZIP and running `AreaGrab.exe` creates
  `data\settings.json` and `data\logs\areagrab.log` next to the exe; no AppData
  writes are needed.

## Not done yet (planned)

- Annotations, pin, OCR, disk history, copy-as-file — **1.2 Pro**.
- Licensing, trial, purchase flow, pricing page checkout — **1.2**.
- English UI localization (site is EN/RU; app UI is RU only).
- Include-cursor, magnifier, delay countdown, update checker.
- Code signing; trusted publisher; SmartScreen reputation.
- Cloud sharing and AI actions — **1.3**, only after validation.
- Website analytics/UTM and Pro waitlist form backend (currently `mailto:`).
- Mixed-DPI multi-monitor hardware matrix; ARM64.
- Installer installation test on a clean VM. In this sandboxed session the installer reaches the Start Menu/HKCU writes and gets access denied; see the diagnosis below. The portable ZIP is the verified fallback.

## Installer temp-folder error (diagnosed 15.11.2026)

**Symptom:** Inno Setup shows “Невозможно создать папку
`C:\Users\<user>\AppData\Local\Temp\is-XXXX.tmp`. Ошибка 5: Отказано в доступе.”

**What we found:** with `TEMP` redirected to a writable folder, the installer gets
past that point, copies all files, then fails creating
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\AreaGrab` and the HKCU uninstall
key with the same error 5. That means the setup process is running with a
restricted token/security policy (for example, launched from a sandbox or a
restricted file-card/shell), not with the normal interactive user token. The
AreaGrab payload itself is fine: the portable build starts, installs the
keyboard hook and registers `PrtScr` from the same folder.

**Workarounds that work today**
- Use `AreaGrab_1.1.0_portable.zip`: extract to Desktop/Documents and run
  `AreaGrab.exe`. No installer, temp folder, registry or Start Menu writes.
- Run `Install-AreaGrab.cmd` instead of the setup exe: it redirects `TEMP`/`TMP`
  to `installer-temp` next to the installer.
- Run the installer from a normal Explorer session outside the agent/sandbox,
  preferably with “Run as administrator” if the account is restricted.

**Recommendation:** test the installer on a clean Windows 10/11 VM as a normal
user before publishing. If it still fails there, ship the portable ZIP as the
primary download and investigate the machine's Start Menu/HKCU permissions or
security software.

## Known issues / risks

1. **Unsigned build.** SmartScreen shows “Unknown publisher”. The site explains this and publishes SHA-256. Signing requires a certificate; see `docs/PLAN.md` §8.4.
2. **`pystray` UIPI warning.** On restricted tokens `ChangeWindowMessageFilterEx` returns access denied; `areagrab/ui/tray.py` tolerates it and continues. On a normal user desktop the icon should appear. Verify on a clean Windows VM.
3. **Overlay performance.** The selection updates at ~30 fps with `ImageTk.PhotoImage` crops. It worked on 3840×1080; 4K multi-monitor needs a benchmark.
4. **UI language.** Russian only in the app; the website has EN/RU.
5. **Build paths.** PyInstaller output is `dist_final\AreaGrab`; installer source points there. `build\AreaGrab` from the old build is stale; remove it once permissions allow.
6. **Site hash.** The SHA-256 in `Сайт/index.html`/`ru.html` must be updated every time the installer is rebuilt.
7. **Installer `AppId`.** Generated GUID is fixed; do not change it between releases or upgrades will install side-by-side.
8. **No update checker.** `advanced.check_updates` exists in settings but no network code runs.

## Next step (recommended)

1. Test installer on a clean Windows 10/11 VM as a non-admin user.
2. Rebuild installer after any code/legal change; update SHA-256 on both site pages and copy to `Сайт/downloads/`.
3. Validate Pro demand: add a “Хочу Pro” button/email form and collect 20 preorders or 100 emails in 30 days before building annotations/licensing.
4. Then start 1.2 Pro: annotations → pin → OCR → disk history → licensing/purchase.
