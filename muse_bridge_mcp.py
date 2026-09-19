#!/usr/bin/env python3
"""
Muse Bridge MCP server -- dispatch work to your AI agent from any MCP host.

Five tools (stdio transport, stdlib only):
  muse_task   {prompt, system?}                              -> chat task, returns text
  muse_image  {prompt, filename?}                            -> PNG saved to ~/dev-fleet/out/
  muse_say    {text, filename?}                              -> TTS mp3 saved to ~/dev-fleet/out/
  muse_video  {prompt, filename?}                            -> ~10s mp4 saved to ~/dev-fleet/out/
  muse_batch  {tasks, wait?, timeout_s?}                     -> queue N tasks at once,
                                                               optionally wait and collect

Talks to muse_bridge.py on localhost (must be running). Reads the LAN key
from ~/.muse-bridge/config.json.

MCP hosts (configs in mcp/):
  Claude Code : claude mcp add muse-bridge -- python C:\\apps\\muse\\muse_bridge_mcp.py
  Codex CLI   : [mcp_servers.muse-bridge] in ~/.codex/config.toml
  opencode    : "mcp" block in opencode.json
  Cline       : mcpServers in cline_mcp_settings.json
  goose       : extensions block in ~/.config/goose/config.yaml
"""

import base64
import json
import os
import sys
import time
import urllib.request

CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".muse-bridge", "config.json")
OUT_DIR = os.path.join(os.path.expanduser("~"), "dev-fleet", "out")
TIMEOUT = 920          # just over the endpoint's 900s hold-open
POLL_EVERY = 30        # seconds between batch status polls


def cfg():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def base():
    return "http://127.0.0.1:%d" % cfg().get("port", 8472)


def _req(method, path, body=None):
    c = cfg()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base() + path, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + c["lan_key"]},
        method=method)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        raw = r.read()
        return raw, r.headers.get_content_type()


def post(path, body):
    return json.loads(_req("POST", path, body)[0].decode())


def get(path):
    return json.loads(_req("GET", path)[0].decode())


def save_media(kind, b64, filename=None):
    """Decode base64 worker payload to OUT_DIR. Returns the saved path."""
    os.makedirs(OUT_DIR, exist_ok=True)
    ext = {"image": ".png", "audio": ".mp3", "video": ".mp4"}[kind]
    default = {"image": "muse-img-%d.png", "audio": "muse-say-%d.mp3",
               "video": "muse-vid-%d.mp4"}[kind]
    name = filename or (default % int(time.time()))
    if not name.lower().endswith(ext):
        name += ext
    dest = os.path.join(OUT_DIR, name)
    with open(dest, "wb") as f:
        f.write(base64.b64decode(b64))
    return dest


def tool_muse_task(args):
    messages = []
    if args.get("system"):
        messages.append({"role": "system", "content": args["system"]})
    messages.append({"role": "user", "content": args["prompt"]})
    resp = post("/v1/chat/completions",
                {"model": "muse-bridge", "messages": messages, "stream": False})
    try:
        text = resp["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        text = json.dumps(resp)
    return [{"type": "text", "text": text}]


def tool_muse_image(args):
    resp = post("/v1/images/generations", {"prompt": args["prompt"]})
    try:
        b64 = resp["data"][0]["b64_json"]
    except (KeyError, IndexError):
        return [{"type": "text",
                 "text": "image request failed: " + json.dumps(resp)[:500]}]
    dest = save_media("image", b64, args.get("filename"))
    return [{"type": "text",
             "text": "Image saved to %s\nPrompt: %s" % (dest, args["prompt"])}]


def tool_muse_say(args):
    raw, _ctype = _req("POST", "/v1/audio/speech",
                       {"input": args["text"], "response_format": "mp3"})
    dest = save_media("audio", base64.b64encode(raw).decode(),
                      args.get("filename"))
    return [{"type": "text",
             "text": "Audio saved to %s (%d bytes)" % (dest, len(raw))}]


def tool_muse_video(args):
    resp = post("/v1/videos/generations", {"prompt": args["prompt"]})
    try:
        b64 = resp["data"][0]["b64_json"]
        note = resp["data"][0].get("note", "")
    except (KeyError, IndexError):
        return [{"type": "text",
                 "text": "video request failed: " + json.dumps(resp)[:500]}]
    dest = save_media("video", b64, args.get("filename"))
    text = "Video saved to %s\nPrompt: %s" % (dest, args["prompt"])
    if note:
        text += "\n" + note
    return [{"type": "text", "text": text}]


def _batch_item_payload(item):
    """Map a {kind, text, ...} item to the bridge's batch task shape."""
    kind = item.get("kind", "chat")
    text = item.get("text", "")
    if kind == "chat":
        msgs = []
        if item.get("system"):
            msgs.append({"role": "system", "content": item["system"]})
        msgs.append({"role": "user", "content": text})
        return {"kind": "chat", "messages": msgs}
    if kind in ("image", "video"):
        return {"kind": kind, "prompt": text}
    if kind == "audio":
        return {"kind": "audio", "input": text}
    raise ValueError("unknown task kind: %s" % kind)


def _batch_summary(bid, data, filenames):
    """Render one text summary of a batch poll response, saving media."""
    lines = ["Batch %s: %d/%d done" % (bid, data.get("done", 0),
                                       data.get("total", 0))]
    for i, t in enumerate(data.get("tasks", [])):
        kind = t.get("kind", "?")
        status = t.get("status", "?")
        res = t.get("result") or {}
        label = "task %d (%s)" % (i + 1, kind)
        if isinstance(res, dict) and res.get("error"):
            lines.append("[failed] %s: %s" % (label, res["error"]))
        elif status not in ("done", "failed"):
            lines.append("[%s] %s" % (status, label))
        elif kind == "chat":
            content = res.get("content", "") if isinstance(res, dict) else str(res)
            lines.append("[ok] %s: %s" % (label, content[:400]))
        else:
            b64 = res.get("b64") if isinstance(res, dict) else None
            if b64:
                try:
                    dest = save_media(kind, b64,
                                      (filenames or {}).get(i))
                    lines.append("[ok] %s: saved to %s" % (label, dest))
                except Exception as exc:  # noqa: BLE001
                    lines.append("[failed] %s: could not save (%s)" % (label, exc))
            else:
                lines.append("[failed] %s: no media in result" % label)
    return "\n".join(lines)


def tool_muse_batch(args):
    tasks = args.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return [{"type": "text", "text": "tasks must be a non-empty array"}]
    try:
        payloads = [_batch_item_payload(t) for t in tasks]
    except ValueError as exc:
        return [{"type": "text", "text": str(exc)}]
    try:
        resp = post("/v1/batches", {"tasks": payloads})
    except Exception as exc:  # noqa: BLE001
        return [{"type": "text", "text": "batch queue failed: %s" % exc}]
    bid = resp.get("id", "?")
    filenames = {i: t.get("filename") for i, t in enumerate(tasks)
                 if t.get("filename")}
    if not args.get("wait", True):
        return [{"type": "text",
                 "text": "Batch %s queued (%d tasks). Poll GET /v1/batches/%s "
                         "or re-run this tool with wait:true to collect."
                         % (bid, len(tasks), bid)}]
    deadline = time.time() + int(args.get("timeout_s", 1200))
    data = None
    while time.time() < deadline:
        time.sleep(POLL_EVERY)
        try:
            data = get("/v1/batches/" + bid)
        except Exception:  # noqa: BLE001
            continue
        if data.get("status") == "done":
            break
    if data is None:
        return [{"type": "text",
                 "text": "Batch %s: could not reach bridge to poll." % bid}]
    text = _batch_summary(bid, data, filenames)
    if data.get("status") != "done":
        text += ("\n\nTimed out waiting — %d/%d done. Re-run with wait:true "
                 "(or poll /v1/batches/%s) to collect the rest."
                 % (data.get("done", 0), data.get("total", 0), bid))
    return [{"type": "text", "text": text}]


TOOLS = {
    "muse_task": (tool_muse_task,
                  "Ask Muse Bridge to do a well-specified task and return the result. "
                  "Best for research, review, writing, and anything where full project "
                  "context helps. Not for tight edit/compile loops (minutes of latency).",
                  {"type": "object",
                   "properties": {"prompt": {"type": "string"},
                                  "system": {"type": "string"}},
                   "required": ["prompt"]}),
    "muse_image": (tool_muse_image,
                   "Ask Muse Bridge to generate an image. Returns the saved file path.",
                   {"type": "object",
                    "properties": {"prompt": {"type": "string"},
                                   "filename": {"type": "string"}},
                    "required": ["prompt"]}),
    "muse_say": (tool_muse_say,
                 "Ask Muse Bridge to read text aloud (TTS). Returns the saved mp3 path.",
                 {"type": "object",
                  "properties": {"text": {"type": "string"},
                                 "filename": {"type": "string"}},
                  "required": ["text"]}),
    "muse_video": (tool_muse_video,
                   "Ask Muse Bridge to generate a ~10s video clip from a prompt. "
                   "Returns the saved mp4 path.",
                   {"type": "object",
                    "properties": {"prompt": {"type": "string"},
                                   "filename": {"type": "string"}},
                    "required": ["prompt"]}),
    "muse_batch": (tool_muse_batch,
                   "Queue several tasks at once (chat/image/audio/video) and collect "
                   "the results. Each task: {kind, text, filename?, system?}. "
                   "wait:false returns the batch id immediately; wait:true (default) "
                   "polls up to timeout_s (default 1200).",
                   {"type": "object",
                    "properties": {
                        "tasks": {"type": "array", "items": {
                            "type": "object",
                            "properties": {
                                "kind": {"type": "string",
                                         "enum": ["chat", "image", "audio", "video"]},
                                "text": {"type": "string"},
                                "filename": {"type": "string"},
                                "system": {"type": "string"}},
                            "required": ["kind", "text"]}},
                        "wait": {"type": "boolean"},
                        "timeout_s": {"type": "integer"}},
                    "required": ["tasks"]}),
}


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        mid = msg.get("id")
        method = msg.get("method", "")

        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "muse-bridge", "version": "1.0"}}})
        elif method == "notifications/initialized":
            pass  # no response for notifications
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": [
                {"name": n, "description": d, "inputSchema": s}
                for n, (_, d, s) in TOOLS.items()]}})
        elif method == "tools/call":
            name = msg["params"]["name"]
            args = msg["params"].get("arguments", {})
            try:
                content = TOOLS[name][0](args)
                send({"jsonrpc": "2.0", "id": mid,
                      "result": {"content": content, "isError": False}})
            except KeyError:
                send({"jsonrpc": "2.0", "id": mid,
                      "result": {"content": [{"type": "text", "text": "unknown tool: " + name}],
                                 "isError": True}})
            except Exception as exc:  # noqa: BLE001 -- report, don't crash
                send({"jsonrpc": "2.0", "id": mid,
                      "result": {"content": [{"type": "text",
                                             "text": "muse-bridge worker error: %s" % exc}],
                                 "isError": True}})
        elif method in ("ping",):
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        else:
            if mid is not None:
                send({"jsonrpc": "2.0", "id": mid,
                      "error": {"code": -32601, "message": "unknown method: " + method}})


if __name__ == "__main__":
    main()
