# -*- mode: python ; coding: utf-8 -*-
# MuseBridge.exe -- single-file build of the bridge + MCP server.
#
# Build ON WINDOWS (PyInstaller cannot cross-build):
#   pip install pyinstaller
#   cd C:\Users\<you>\apps\muse
#   pyinstaller MuseBridge.spec
# Output: dist\MuseBridge.exe  (interpreter + both scripts, no console)
#
# Run it: double-click -> bridge starts in tray mode (flower by the clock).
# MCP hosts: point them at MuseBridge.exe with the argument --mcp.

block_cipher = None

a = Analysis(
    ['muse_bridge.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['muse_bridge_mcp'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MuseBridge',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,   # no console window -- like pythonw; the tray is the UI.
                     # (MCP stdio still works: hosts spawn it with pipes.)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='muse-bridge.ico',
)
