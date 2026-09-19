# Muse Bridge — setup guide

> **Preferred route:** build the one-file exe (`BUILD-EXE.md`:
> `pyinstaller MuseBridge.spec`) and double-click `dist\MuseBridge.exe` —
> bridge in tray mode, MCP server inside via `--mcp`, no console. The
> script route below does the same thing and is handy for tinkering.

Your tools talk to your AI agent through **Muse Bridge**, an OpenAI-compatible
front door running on your workstation. Your tools send tasks through a
tunnel, the agent works them, and returns the answers. Three pieces:

1. **`muse_bridge.py`** — runs on your workstation (Windows). OpenAI-shaped
   routes for local tools + a task queue for your agent.
2. **`muse_bridge_mcp.py`** — optional. Lets Claude Code dispatch work as
   worker tools, the same pattern as a subagent.
3. **The worker** — runs on your agent's side on a schedule. Nothing for you
   to install; it activates when you say the tunnel is up.

## Step 1 — run the bridge (workstation)

Python 3, stdlib only, no packages to install.

```powershell
mkdir C:\muse-bridge
# copy muse_bridge.py into it
cd C:\muse-bridge
python muse_bridge.py
```

First run prints two secrets **once** and stores them in
`C:\Users\<you>\.muse-bridge\config.json` (file mode 600):

- **LAN bearer key** — goes into your local tools (anything with a base_url +
  api_key + model field). Model name: `muse-bridge`.
- **Queue path** (`/q/<random>/`) — you will give this to your agent with the
  tunnel URL. Never put it in a tool config; it's only for the tunnel.

The server binds `127.0.0.1:8472` only. Keep it running (a scheduled task or a
terminal you leave open). The console becomes a live dashboard (see below).

**Task-tray mode (optional).** Run `python muse_bridge.py --tray` and the
console hides, leaving a teal icon by the clock: right-click for live queue
counts, show/hide the dashboard, or quit; double-click toggles the console.
Task completions pop a notification. No packages needed — it's stdlib
`ctypes`, and any failure falls back to the normal console. For no window at
all (tray becomes the whole UI), launch with `pythonw.exe` instead of
`python.exe`. Note: on the very first run the console stays visible so you
can copy the two secrets it prints once.

Quick test (new terminal):

```powershell
$body = @{model="muse-bridge"; stream=$false; messages=@(@{role="user"; content="Reply with the word: online"})} | ConvertTo-Json -Depth 5
$body | curl.exe -s -X POST http://127.0.0.1:8472/v1/chat/completions -H "Authorization: Bearer $key" -H "Content-Type: application/json" --data-binary "@-"
```

The request hangs until your agent's worker picks it up (a few minutes the first
time) — that's the design, not a bug. The connection is held open up to
15 minutes; after that you get a 504 and can poll `GET /v1/tasks/<id>`.

## Step 2 — tunnel (your choice)

Your agent's worker needs to reach the **queue paths only**: `/q/<cap>/pending`,
`/q/<cap>/result/<id>`, `/q/<cap>/status`. Never expose the whole port.

**Option A — Tailscale Funnel (simplest).** This gives a public URL on your
tailnet domain, e.g. `https://<host>.tail12345.ts.net`, reachable from the
internet — which is what your agent's worker needs, since it is not on your
tailnet:

```powershell
tailscale funnel --bg http://127.0.0.1:8472
```

Note: `tailscale serve` is the tailnet-ONLY variant. Fine for your own
devices, but useless here — your agent's worker could never reach a serve URL.
Use `funnel` for the queue. Anyone with the URL can knock, but the queue
paths hide behind the unguessable cap, and the `/v1/*` routes still demand
your LAN bearer key (which never leaves your machines).

**Option B — Cloudflare Tunnel.** In the tunnel's ingress config, expose only
the queue path:

```yaml
ingress:
  - hostname: muse-bridge-queue.example.com
    path: /q/<cap>/*
    service: http://127.0.0.1:8472
  - service: http_status:404
```

Put Cloudflare Access (or equivalent) in front if you want identity checks on
top. The random path is defense-in-depth, not the primary lock.

## Step 3 — tell your agent

Message your agent: **"queue is up at `<tunnel-url>` with cap path `/q/<...>/`"**.
It stores it, enables its queue worker (polls every ~5 minutes) and the
morning digest, and confirms with a live round-trip test.

## Step 4 — Claude Code worker (optional)

```powershell
# copy muse_bridge_mcp.py next to the bridge, then:
claude mcp add muse-bridge -- python C:\muse-bridge\muse_bridge_mcp.py
```

Restart Claude Code. Three tools appear: `mcp__muse_bridge__muse_task`,
`mcp__muse_bridge__muse_image`, `mcp__muse_bridge__muse_say`. Dispatch work
the way you'd dispatch a subagent — best for well-specified tasks where full
context beats raw speed.

## Using it

**Chat** (any OpenAI-compatible client — curl, opencode, Cline, Tavo):

```bash
$body | curl.exe -s -X POST http://127.0.0.1:8472/v1/chat/completions \
  -H "Authorization: Bearer $key" -H "Content-Type: application/json" --data-binary "@-"
```

**Images** — `POST /v1/images/generations` `{"prompt": "..."}` → OpenAI-style
`{data:[{b64_json}]}`. **Audio** — `POST /v1/audio/speech` `{"input": "..."}`
→ raw mp3 bytes. **Video** — `POST /v1/videos/generations` `{"prompt": "..."}`
→ base64 mp4; clips are ~10 seconds, stitch for longer.

**Overnight batches** — queue N tasks in one call, collect in the morning:

```bash
curl http://127.0.0.1:8472/v1/batches \
  -H "Authorization: Bearer $key" -H "Content-Type: application/json" -d '{
    "tasks": [
      {"kind": "chat",  "messages": [{"role": "user", "content": "Task one..."}]},
      {"kind": "image", "prompt": "A beacon mascot, art deco..."},
      {"kind": "audio", "input": "Read this aloud..."}
    ]
  }'
# -> {"id": "batch_...", "task_ids": [...]}
# morning: GET /v1/batches/batch_...  -> per-task status + results
```

Your agent's morning digest (7:30 AM PT) summarizes what the overnight worker
completed, failed, or flagged — you don't even need to poll.

## The console dashboard & local action log

The server window is a live dashboard: every queued task with its status and
risk on **two axes**:

- **Security** (color) — 🟢 LOW: just making something for you, nothing on
  this PC changes (image/audio/video) · 🟡 MEDIUM: open-ended work (chat),
  review the answer · 🔴 HIGH: batches, many things at once.
- **Latency** (word) — FAST: one worker cycle (chat) · MEDIUM: generation
  takes minutes (image/audio) · SLOW: video/batches, settle in.

Whenever a result reports files the worker touched, they're cited under the
task on the dashboard (as the worker's report), with a review nudge when the
security color isn't green. Risk is assessed locally by task kind — the
bridge can't see inside a task, so chat is never green. Every lifecycle event (queued → claimed → done/failed)
is also appended to `~/.muse-bridge/actions.log` as JSONL: timestamp, task,
summary, risk, and any files the worker reported touching. That file is written
**only** by this process on this PC — the queue protocol has no route to read
or change it. If a result claims files were touched, the log marks it as the
worker's own report.

## Limits, honestly stated

- **Latency is minutes, not seconds.** your agent's worker polls every ~5 minutes
  and media generation takes minutes more. Task granularity, not tight loops.
- **Video**: ~10s clips, synthesized sound from a text mood description, no
  audio input. Longer = multiple clips stitched.
- **Audio**: speech/TTS and podcast-style voices only. No song identification
  or music retrieval.
- **Sizes**: media comes back base64 (~33% inflation). Big videos get heavy;
  keep requests modest.
- **Destructive actions**: your agent asks first. The worker answers and generates;
  it doesn't run irreversible operations without your confirmation.
- **Streaming**: not supported (`stream:false` only).

## Troubleshooting

- `401` — wrong bearer key. Re-copy from `~/.muse-bridge/config.json`.
- Request hangs then 504 — worker hasn't picked it up yet (tunnel down? worker
  disabled?). Poll `GET /v1/tasks/<id>`; the result lands when the worker
  gets to it.
- `502 worker error` — your agent tried and failed; the message says why.
- Port in use — another copy is running, or change `PORT` at the top of the
  script (and the MCP script reads the port from config automatically).
