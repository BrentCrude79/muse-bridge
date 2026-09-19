# Muse Bridge MCP — install for your coding host

One server, five tools (`muse_task`, `muse_image`, `muse_say`, `muse_video`,
`muse_batch`), stdio, stdlib only. The bridge (`muse_bridge.py`) must be
running — the MCP server talks to it on `127.0.0.1:8472` and reads your LAN
key from `~/.muse-bridge/config.json`.

**1. Copy the files** — everything here goes on the workstation, e.g.:

```powershell
xcopy \\path\\to\\muse-bridge C:\apps\muse\ /E /I
```

(The repo's root files — `muse_bridge.py`, `SETUP.md`, `README.md` — can live
there too. Point each config below at wherever `muse_bridge_mcp.py`
lands.)

**2. Register with your host** — pick your section:

---

## Claude Code

```powershell
claude mcp add muse-bridge -- python C:\apps\muse\muse_bridge_mcp.py
```

Restart Claude Code. Tools appear as
`mcp__muse_bridge__muse_task`, `…_muse_image`, `…_muse_say`,
`…_muse_video`, `…_muse_batch`.

## Codex CLI

`~/.codex/config.toml`:

```toml
[mcp_servers.muse-bridge]
command = "python"
args = ["C:\\apps\\muse\\muse_bridge_mcp.py"]
```

## opencode

`opencode.json` (project root or `~/.config/opencode/`):

```json
{
  "mcp": {
    "muse-bridge": {
      "type": "local",
      "command": ["python", "C:\\apps\\muse\\muse_bridge_mcp.py"],
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
      "command": "python",
      "args": ["C:\\apps\\muse\\muse_bridge_mcp.py"],
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
    cmd: python
    args:
      - C:\apps\muse\mcp\muse_bridge_mcp.py
```

---

## The other platforms (not MCP hosts)

**SillyTavern, OpenWebUI, Tavo, zcode, hermes, ohmypi** don't speak MCP —
they speak OpenAI-style HTTP, which the bridge already is. Point them at
`http://127.0.0.1:8472` with your LAN bearer key and model `muse-bridge`
(see `README.md` → "Connect your tools").

## If `python` isn't on PATH

Replace `python` with the full path to your Python, e.g.
`C:\\Python313\\python.exe` (or `py -3`).

## Smoke test

Any host: call `muse_task` with `{"prompt": "Reply with the word: online"}`.
Your agent's worker claims it within ~5 minutes and the text comes back.
