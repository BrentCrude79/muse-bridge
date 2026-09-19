# Building MuseBridge.exe

One file: the bridge (always tray mode) + the MCP server (`--mcp`).
Build it on the Windows machine — PyInstaller can't cross-build.

## One-time build

```bat
pip install pyinstaller
cd C:\Users\brent\apps\muse
pyinstaller MuseBridge.spec
```

Result: `dist\MuseBridge.exe` (~10–15 MB, flower icon, no console).

Copy it wherever you like, e.g. `C:\Users\brent\apps\muse\MuseBridge.exe`.

## Run

- **Double-click** → bridge starts, flower parks by the clock. No console, ever.
- Right-click the flower → Status / Show dashboard / Quit.
- First run pops one dialog with the LAN key + queue path — save them.

## MCP hosts

Point each host at the exe with the argument `--mcp`
(the bridge itself must already be running — double-click the exe first):

- Claude Code: `claude mcp add muse-bridge -- C:\Users\brent\apps\muse\MuseBridge.exe --mcp`
- Codex / opencode / Cline / goose: command `...\MuseBridge.exe`, args `["--mcp"]`

(Configs in `mcp/` are already written this way.)

## Notes

- Unsigned → Windows SmartScreen will ask once; that's expected.
- The exe reads the same `%USERPROFILE%\.muse-bridge\config.json` as the scripts,
  so keys carry over — no reconfiguration.
- To rebuild after an update: re-run `pyinstaller MuseBridge.spec`.
