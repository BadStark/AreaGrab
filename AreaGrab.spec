# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

# AreaGrab 1.1 — onedir build for a fast start and fewer antivirus false positives.
# The installer (Inno Setup) packages dist\AreaGrab\*.

a = Analysis(
    ['AreaGrab.py'],
    pathex=[],
    binaries=[],
    datas=[('areagrab_v2.png', '.')],
    hiddenimports=['pystray._win32'] + collect_submodules('areagrab'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['keyboard', 'numpy', 'scipy', 'matplotlib', 'pandas', 'pytest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AreaGrab',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['areagrab_v2.ico'],
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='AreaGrab',
)
