# Windows upgrade acceptance checklist

Run on a real Windows 10/11 machine. CI validates the build and silent install,
but cannot replace interactive upgrade and tray verification.

| Scenario | Expected outcome |
| --- | --- |
| Clean install, app not running | Install succeeds, app launches once |
| Upgrade with AreaGrab running | Installer asks to exit; Retry after tray Exit continues |
| Upgrade with app running, Cancel | Installer stops; existing install remains usable |
| Silent upgrade while app running | Installation fails safely without force-terminating AreaGrab |
| Upgrade after app exits | Existing settings and saved screenshots remain |
| Upgrade from older AreaGrab 1.1 | Same AppId and installation folder are reused |
| Run new installer twice | No duplicate installed app or startup entry |
| Uninstall | Application files removed; user screenshots outside install dir remain |
| Portable AreaGrab running | Installer does not force-close it; user must exit it |
| History item saved on disk | Click copies image and opens saved file |
| History item RAM-only | Click copies image and opens internal preview |
| History navigation | Previous/next pages work without duplicates |
| Pause / resume | Both hotkeys disabled during pause; resume restores them |
| New screenshot | Tray shows PrtScr; hotkey still captures |
| Repeat screenshot | Tray shows Ctrl+PrtScr; repeat uses previous rectangle |

**Important:** This is an acceptance checklist, not a claim that all cases have
already passed. Manual verification is required before releasing to users.
