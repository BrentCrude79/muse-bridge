# Muse Bridge MCP — install for your coding host

One server, five tools (`muse_task`, `muse_image`, `muse_say`, `muse_video`,
`muse_batch`), stdio, stdlib only. The bridge must be running — the MCP
server talks to it on `127.0.0.1:8472` and reads your LAN key from
`~/.muse-bridge/config.json`.

**1. Build the exe** (one time — see `BUILD-EXE.md`):

```bat
pip install pyinstaller
cd C:\Users\brent\apps\muse
pyinstaller MuseBridge.spec
copy dist\MuseBridge.exe C:\Users\brent\apps\muse\
```

Then **double-click `MuseBridge.exe`** — the bridge starts in tray mode
(flower by the clock). The MCP server is inside the same file.

**2. Register with your host** — pick your section:

---

## Claude Code

```powershell
claude mcp add muse-bridge -- C:\Users\brent\apps\muse\MuseBridge.exe --mcp
```

Restart Claude Code. Tools appear as
`mcp__muse_bridge__muse_task`, `…_muse_image`, `…_muse_say`,
`…_muse_video`, `…_muse_batch`.

## Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.muse-bridge]
command = "C:\\Users\\brent\\apps\\muse\\MuseBridge.exe"
args = ["--mcp"]
```

## opencode

`opencode.json` (project root or `~/.config/opencode/`):

```json
{
  "mcp": {
    "muse-bridge": {
      "type": "local",
      "command": ["C:\\Users\\brent\\apps\\muse\\MuseBridge.exe", "--mcp"],
      "enabled": true
    }
  }
}
```

## Cline (VS Code)

`cline_mcp_settings.json` (Cline → MCP Servers → Configure):

```json
{
  "mcpServers": {
    "muse-bridge": {
      "command": "C:\\Users\\brent\\apps\\muse\\MuseBridge.exe",
      "args": ["--mcp"],
      "disabled": false
    }
  }
}
```

## goose (Block)

`~/.config/goose/config.yaml`:

```yaml
extensions:
  muse-bridge:
    enabled: true
    type: stdio
    name: muse-bridge
    cmd: C:\Users\brent\apps\muse\MuseBridge.exe
    args:
      - --mcp
```

---

## The other platforms (not MCP hosts)

**SillyTavern, OpenWebUI, Tavo, zcode, hermes, ohmypi** don't speak MCP —
they speak OpenAI-style HTTP, which the bridge already is. Point them at
`http://127.0.0.1:8472` with your LAN bearer key and model `muse-bridge`
(see `README.md` → "Connect your tools").

## No-exe alternative

Rather not build? The scripts run as-is: bridge via
`pythonw.exe muse_bridge.py --tray`, MCP via
`python muse_bridge_mcp.py` (put that command + no args in the configs
above instead of the exe).

## Smoke test

Any host: call `muse_task` with `{"prompt": "Reply with the word: online"}`.
Your agent's worker claims it within ~5 minutes and the text comes back.
