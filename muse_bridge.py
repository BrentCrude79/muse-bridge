#!/usr/bin/env python3
"""
Muse Bridge front-door -- OpenAI-compatible endpoint for local tools + task queue for your AI agent.

Two sides, one script:

  LOCAL TOOLS -> OpenAI-shaped routes on 127.0.0.1:8472 (bearer key required).
      POST /v1/chat/completions      {messages:[...]}            -> chat completion
      POST /v1/images/generations    {prompt}                   -> {data:[{b64_json}]}
      POST /v1/audio/speech          {input}                    -> raw audio bytes
      POST /v1/videos/generations    {prompt}                   -> {data:[{b64_json,format}]}
      POST /v1/batches               {tasks:[...]}              -> {id, task_ids} (overnight)
      GET  /v1/models                                           -> [{id:"muse-bridge"}]
      GET  /v1/tasks/<id>                                       -> poll a single task
      GET  /v1/batches/<id>                                     -> poll a whole batch

  AGENT (your AI assistant) -> queue routes, reached through YOUR tunnel only.
      GET  /q/<cap>/pending?claim=1   list (and claim) waiting tasks
      POST /q/<cap>/result/<id>       {"result": {...}}  deliver an answer
      GET  /q/<cap>/status            queue counts

How a request flows: the tool POSTs, the script queues the task and holds the
HTTP connection open (up to WAIT_TIMEOUT). the agent's worker polls /pending
every few minutes, works the task, POSTs the result back; the script then
completes the waiting client connection with a normal-looking response.

LOCAL DASHBOARD + ACTION LOG (this is the part you watch):
  - The console shows a live dashboard: every queued task, its status, and
    risk on two axes -- SECURITY as color (green = just making something for
    you, yellow = open-ended, review the answer, red = many things at once)
    and LATENCY as a word (FAST = one worker cycle, MEDIUM = generation takes
    minutes, SLOW = video/batches, settle in). Files the worker reports
    touching are cited under the task, with a review nudge when security
    isn't green.
  - Every task lifecycle event is appended to ~/.muse-bridge/actions.log
    as JSONL. That file is written ONLY by this process on this PC. Nothing in
    the queue protocol can read it, change it, or delete it -- the agent's worker
    can only *report* what it did inside its result payload, and the log marks
    such reports as the worker's own claim.

Stdlib only.  Run:   python muse_bridge.py
First run prints the LAN key and queue capability path ONCE and stores them in
~/.muse-bridge/config.json -- that file is secret, keep it private.
Task-tray mode:  python muse_bridge.py --tray   (Windows; icon by the clock,
right-click for status, notifications on task completion)
"""

import base64
import collections
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

VERSION = "2.4"               # bump on every behavior change. Shown in the
                              # dashboard header, the tray tooltip, and
                              # `python muse_bridge.py --version`.
PORT = 8472
WAIT_TIMEOUT = 900            # seconds a client connection is held open
MAX_BODY = 96 * 1024 * 1024   # max request body (media results are large)

HAS_CONSOLE = sys.stdout is not None  # False under pythonw.exe


def say(msg):
    """print() that survives pythonw (where stdout is None)."""
    if HAS_CONSOLE:
        print(msg)

CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".muse-bridge")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
ACTIONS_LOG = os.path.join(CONFIG_DIR, "actions.log")  # local only, append-only

# ---------- console colors (ANSI; enabled on Windows 10+ below) ----------
GREEN, YELLOW, RED, CYAN, DIM, RESET = (
    "\x1b[32m", "\x1b[33m", "\x1b[31m", "\x1b[36m", "\x1b[2m", "\x1b[0m")

if os.name == "nt" and HAS_CONSOLE:
    # No-op that enables ANSI escape processing on Windows. Skipped under
    # pythonw: with no console it would spawn a stray cmd window.
    os.system("")

# Risk is assessed LOCALLY by task kind, on two axes. The endpoint cannot
# see inside a task, so "chat" (open-ended agent work) is never green.
#   security -> shown as COLOR: LOW (green) just making something for you;
#       MEDIUM (yellow) open-ended, review it; HIGH (red) many things at once.
#   latency -> shown as a WORD: FAST = one worker cycle; MEDIUM = generation
#       takes minutes; SLOW = video/batches, settle in.
RISK = {
    "image": ("LOW", GREEN,
              "Just making something for you -- nothing on this PC changes."),
    "audio": ("LOW", GREEN,
              "Just making something for you -- nothing on this PC changes."),
    "video": ("LOW", GREEN,
              "Just making something for you -- nothing on this PC changes."),
    "chat": ("MEDIUM", YELLOW,
             "Open-ended -- your agent decides how to handle it. Give the answer a look."),
    "batch": ("HIGH", RED,
              "Many things at once -- review each result when it lands."),
}

LATENCY = {
    "chat": "FAST",      # one worker cycle, no generation
    "image": "MEDIUM",   # generation takes minutes
    "audio": "MEDIUM",   # TTS takes a bit
    "video": "SLOW",     # slowest single generation
    "batch": "SLOW",     # many tasks -- finishes when the last one does
}


def latency_of(kind):
    return LATENCY.get(kind, "MEDIUM")

STATUS_COLOR = {"queued": YELLOW, "claimed": CYAN, "done": GREEN,
                "failed": RED, "expired": RED}


def load_or_create_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f), False
    cfg = {
        "lan_key": secrets.token_urlsafe(32),   # local tools -> front door
        "cap": secrets.token_urlsafe(24),       # unguessable queue path prefix
        "port": PORT,
    }
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
    os.chmod(CONFIG_PATH, 0o600)
    return cfg, True


CONFIG, FIRST_RUN = load_or_create_config()
CAP = CONFIG["cap"]

# Task-tray mode: `python muse_bridge.py --tray` hides the console and parks an
# icon by the clock (Windows, stdlib ctypes only). Non-Windows: flag is ignored
# with a warning.
TRAY_MODE = "--tray" in sys.argv

# task_id -> {"kind","payload","batch_id","created","claimed","event","result",
#             "risk","risk_label","summary","files_reported","last_event"}
TASKS = {}
TASKS_LOCK = threading.Lock()
RECENT = collections.deque(maxlen=8)   # (ts, text) for the dashboard feed
DRAW_LOCK = threading.Lock()


def risk_of(kind):
    return RISK.get(kind, ("MEDIUM", YELLOW,
                           "Unknown kind -- review the result when it lands."))


def summarize(kind, payload):
    try:
        if kind == "chat":
            msgs = payload.get("messages", [])
            user_msgs = [m.get("content", "") for m in msgs if m.get("role") == "user"]
            return (user_msgs[-1] if user_msgs else "")[:70]
        if kind in ("image", "video"):
            return str(payload.get("prompt", ""))[:70]
        if kind == "audio":
            return str(payload.get("input", ""))[:70]
    except Exception:
        pass
    return ""


def log_action(event, tid, kind="", summary="", status="", files=None):
    """Append one JSONL line to the LOCAL action log. Only this process writes
    here; the queue protocol has no route to it."""
    risk, _, risk_label = risk_of(kind) if kind else ("", "", "")
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
             "event": event, "id": tid, "kind": kind, "summary": summary,
             "risk": risk, "latency": latency_of(kind) if kind else "",
             "risk_label": risk_label, "status": status,
             "files_reported_by_worker": files or []}
    try:
        with open(ACTIONS_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def age_str(created):
    s = int(time.time() - created)
    if s < 60:
        return "%ds" % s
    if s < 3600:
        return "%dm" % (s // 60)
    return "%dh%dm" % (s // 3600, (s % 3600) // 60)


def task_status_of(t):
    if t["result"] is not None:
        return "failed" if isinstance(t["result"], dict) and "error" in t["result"] else "done"
    return "claimed" if t["claimed"] else "queued"


def draw():
    """Redraw the whole console dashboard. No-op without a console
    (pythonw tray mode) -- the tray tooltip carries the status there."""
    if not HAS_CONSOLE:
        return
    with DRAW_LOCK:
        with TASKS_LOCK:
            items = sorted(TASKS.items(), key=lambda kv: kv[1]["created"])
            counts = {"queued": 0, "claimed": 0, "done": 0, "failed": 0}
            for _, t in items:
                st = task_status_of(t)
                counts["done" if st == "done" else
                       "failed" if st == "failed" else st] += 1
            rows = []
            for tid, t in items[-12:]:
                risk, color, _ = risk_of(t["kind"])
                lat = latency_of(t["kind"])
                st = task_status_of(t)
                rows.append("  %s  %-5s  %s%-6s%s  %-6s  %s%-7s%s  %-4s  %s" % (
                    tid[:12], t["kind"], color, risk, RESET, lat,
                    STATUS_COLOR.get(st, ""), st, RESET,
                    age_str(t["created"]), t["summary"][:36]))
                files = t.get("files_reported") or []
                if files:
                    # cite anything the worker reports touching; nudge review
                    # when the security color isn't green
                    nudge = " -- review these" if risk != "LOW" else ""
                    rows.append("  %s↳ files (worker's report)%s: %s%s" % (
                        DIM, RESET, ", ".join(files)[:90], nudge))
            recent = list(RECENT)
        L = []
        L.append(CYAN + "=" * 70 + RESET)
        L.append("  %sMUSE BRIDGE v%s%s  ·  127.0.0.1:%d  ·  queued %d · claimed %d · done %d · failed %d"
                 % (CYAN, VERSION, RESET, PORT, counts["queued"], counts["claimed"],
                    counts["done"], counts["failed"]))
        L.append(CYAN + "-" * 70 + RESET)
        L.append("  LIVE TASKS")
        L.extend(rows if rows else ["  " + DIM + "(none yet)" + RESET])
        L.append(CYAN + "-" * 70 + RESET)
        L.append("  RECENT")
        L.extend("  %s%s %s%s" % (DIM, ts, RESET, txt) for ts, txt in recent) \
            or L.append("  " + DIM + "(nothing yet)" + RESET)
        L.append(CYAN + "-" * 70 + RESET)
        L.append("  Security %sLOW%s just making something for you · "
                 "%sMEDIUM%s open-ended, review it · "
                 "%sHIGH%s many at once"
                 % (GREEN, RESET, YELLOW, RESET, RED, RESET))
        L.append("  Latency  FAST one worker cycle · MEDIUM generation takes "
                 "minutes · SLOW video/batches, settle in")
        L.append("  Log: %s  (this PC only -- the queue cannot read or change it)"
                 % ACTIONS_LOG)
        sys.stdout.write("\x1b[2J\x1b[H" + "\n".join(L) + "\n")
        sys.stdout.flush()


def note(text):
    RECENT.append((time.strftime("%H:%M:%S"), text))
    draw()


def new_task(kind, payload, batch_id=None):
    tid = "t_" + secrets.token_hex(8)
    summary = summarize(kind, payload)
    with TASKS_LOCK:
        TASKS[tid] = {"kind": kind, "payload": payload, "batch_id": batch_id,
                      "created": time.time(), "claimed": False,
                      "event": threading.Event(), "result": None,
                      "summary": summary, "files_reported": []}
    log_action("queued", tid, kind, summary, "queued")
    note("%squeued%s   %s %s -- %s" % (YELLOW, RESET, tid[:12], kind, summary[:50]))
    return tid


def wait_for_result(tid):
    with TASKS_LOCK:
        ev = TASKS[tid]["event"]
    if ev.wait(WAIT_TIMEOUT):
        with TASKS_LOCK:
            return TASKS[tid]["result"]
    return None


def mark_event(tid, event, status, files=None):
    with TASKS_LOCK:
        t = TASKS.get(tid)
        if not t:
            return
        if files:
            t["files_reported"] = files
        summary, kind = t["summary"], t["kind"]
    log_action(event, tid, kind, summary, status, files)
    color = STATUS_COLOR.get(status, "")
    note("%s%s%s  %s %s -- %s" % (color, event, RESET, tid[:12], kind, summary[:50]))
    if TRAY_MODE and event in ("done", "failed", "expired"):
        tray_notify("Muse Bridge: task %s" % event,
                    "%s -- %s" % (kind, summary[:120]))


def task_status(tid):
    with TASKS_LOCK:
        t = TASKS.get(tid)
        if not t:
            return None
        return {"id": tid, "kind": t["kind"], "batch_id": t["batch_id"],
                "status": task_status_of(t), "result": t["result"]}


class H(BaseHTTPRequestHandler):
    server_version = "muse-bridge/2.1"

    # ---------- helpers ----------
    def _send_json(self, code, obj):
        raw = json.dumps(obj).encode()
        try:
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError):
            # client (or the tunnel proxy) went away mid-response; not an error
            note("client went away mid-response " + DIM +
                 self.path.split("?", 1)[0][:40] + RESET)

    def _err(self, code, message):
        self._send_json(code, {"error": {"message": message, "type": "endpoint_error"}})

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return None
        if n > MAX_BODY:
            return "TOO_BIG"
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw.decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            return None

    def _authed(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        return hmac.compare_digest(auth[7:].strip(), CONFIG["lan_key"])

    def _queue_path(self):
        # returns the sub-path after /q/<cap>/, or None if cap mismatches
        parts = self.path.split("?", 1)[0].split("/")
        if len(parts) >= 3 and parts[1] == "q" and hmac.compare_digest(parts[2], CAP):
            return "/" + "/".join(parts[3:])
        return None

    def log_message(self, *a):
        pass

    # ---------- GET ----------
    def do_GET(self):
        path = self.path.split("?", 1)[0]

        qsub = self._queue_path()
        if qsub is not None:
            return self._queue_get(qsub)

        if not self._authed():
            return self._err(401, "missing or invalid bearer key")

        if path == "/v1/models":
            return self._send_json(200, {"object": "list", "data": [
                {"id": "muse-bridge", "object": "model",
                 "created": int(time.time()), "owned_by": "muse-bridge"}]})

        if path.startswith("/v1/tasks/"):
            st = task_status(path[len("/v1/tasks/"):])
            return self._send_json(200, st) if st else self._err(404, "unknown task")

        if path.startswith("/v1/batches/"):
            bid = path[len("/v1/batches/"):]
            with TASKS_LOCK:
                items = [dict(id=tid, **{k: t[k] for k in ("kind", "batch_id")},
                              status=task_status_of(t), result=t["result"])
                         for tid, t in TASKS.items() if t["batch_id"] == bid]
            if not items:
                return self._err(404, "unknown batch")
            done = sum(1 for i in items if i["status"] in ("done", "failed"))
            return self._send_json(200, {"id": bid,
                                        "status": "done" if done == len(items) else "working",
                                        "done": done, "total": len(items), "tasks": items})

        return self._err(404, "not found")

    def _queue_get(self, qsub):
        if qsub == "/status":
            with TASKS_LOCK:
                counts = {"queued": 0, "claimed": 0, "done": 0}
                for t in TASKS.values():
                    st = task_status_of(t)
                    counts["done" if st == "done" else
                           "queued" if st == "queued" else "claimed"] += 1
            return self._send_json(200, {"counts": counts, "total": len(TASKS)})
        if qsub == "/pending":
            claim = "claim=1" in (self.path.split("?", 1)[1] if "?" in self.path else "")
            out = []
            claimed_ids = []
            with TASKS_LOCK:
                for tid, t in TASKS.items():
                    if t["result"] is None and not t["claimed"]:
                        if claim:
                            t["claimed"] = True
                            claimed_ids.append(tid)
                        out.append({"id": tid, "kind": t["kind"],
                                    "payload": t["payload"], "batch_id": t["batch_id"]})
            for tid in claimed_ids:
                mark_event(tid, "claimed", "claimed")
            return self._send_json(200, {"tasks": out})
        return self._err(404, "not found")

    # ---------- POST ----------
    def do_POST(self):
        path = self.path.split("?", 1)[0]

        qsub = self._queue_path()
        if qsub is not None:
            if qsub.startswith("/result/"):
                return self._queue_result(qsub[len("/result/"):])
            return self._err(404, "not found")

        if not self._authed():
            return self._err(401, "missing or invalid bearer key")

        body = self._read_json()
        if body is None:
            return self._err(400, "invalid JSON body")
        if body == "TOO_BIG":
            return self._err(413, "body too large")

        if path == "/v1/chat/completions":
            return self._handle_chat(body)
        if path == "/v1/images/generations":
            return self._handle_image(body)
        if path == "/v1/audio/speech":
            return self._handle_audio(body)
        if path == "/v1/videos/generations":
            return self._handle_video(body)
        if path == "/v1/batches":
            return self._handle_batch(body)
        return self._err(404, "not found")

    def _queue_result(self, tid):
        body = self._read_json()
        if not isinstance(body, dict) or "result" not in body:
            return self._err(400, 'body must be {"result": {...}}')
        with TASKS_LOCK:
            t = TASKS.get(tid)
            if not t:
                return self._err(404, "unknown task")
            t["result"] = body["result"]
            t["event"].set()
        res = body["result"]
        files = res.get("files") if isinstance(res, dict) else None
        files = files if isinstance(files, list) else None
        st = "failed" if isinstance(res, dict) and "error" in res else "done"
        mark_event(tid, "done" if st == "done" else "failed", st, files)
        return self._send_json(200, {"ok": True})

    def _expired(self, tid):
        mark_event(tid, "expired", "expired")
        return self._err(504, "task %s still pending after %ds; poll GET /v1/tasks/%s"
                         % (tid, WAIT_TIMEOUT, tid))

    def _worker_error(self, res):
        return self._err(502, "worker error: %s" % res["error"])

    # ----- front-door handlers -----
    def _handle_chat(self, body):
        if body.get("stream"):
            return self._err(400, "streaming is not supported; use stream:false")
        msgs = body.get("messages")
        if not isinstance(msgs, list) or not msgs:
            return self._err(400, '"messages" must be a non-empty array')
        tid = new_task("chat", {"messages": msgs, "model": body.get("model", "muse-bridge")})
        res = wait_for_result(tid)
        if res is None:
            return self._expired(tid)
        if isinstance(res, dict) and "error" in res:
            return self._worker_error(res)
        content = res.get("content", "") if isinstance(res, dict) else str(res)
        return self._send_json(200, {
            "id": "chatcmpl-" + tid, "object": "chat.completion",
            "created": int(time.time()), "model": "muse-bridge",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}})

    def _handle_image(self, body):
        prompt = body.get("prompt")
        if not prompt:
            return self._err(400, '"prompt" is required')
        tid = new_task("image", {"prompt": prompt, "size": body.get("size", "1024x1024")})
        res = wait_for_result(tid)
        if res is None:
            return self._expired(tid)
        if not isinstance(res, dict) or "error" in res:
            return self._worker_error(res if isinstance(res, dict) else {"error": res})
        return self._send_json(200, {"created": int(time.time()),
                                    "data": [{"b64_json": res["b64"]}]})

    def _handle_audio(self, body):
        text = body.get("input")
        if not text:
            return self._err(400, '"input" text is required')
        tid = new_task("audio", {"input": text, "voice": body.get("voice", "default"),
                                 "response_format": body.get("response_format", "mp3")})
        res = wait_for_result(tid)
        if res is None:
            return self._expired(tid)
        if not isinstance(res, dict) or "error" in res:
            return self._worker_error(res if isinstance(res, dict) else {"error": res})
        try:
            raw = base64.b64decode(res["b64"])
        except (ValueError, KeyError):
            return self._err(502, "worker returned bad audio data")
        ctype = {"mp3": "audio/mpeg", "wav": "audio/wav"}.get(res.get("format", "mp3"), "audio/mpeg")
        try:
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionAbortedError):
            note("client went away mid-response " + DIM + "(audio)" + RESET)

    def _handle_video(self, body):
        prompt = body.get("prompt")
        if not prompt:
            return self._err(400, '"prompt" is required')
        tid = new_task("video", {"prompt": prompt})
        res = wait_for_result(tid)
        if res is None:
            return self._expired(tid)
        if not isinstance(res, dict) or "error" in res:
            return self._worker_error(res if isinstance(res, dict) else {"error": res})
        return self._send_json(200, {"created": int(time.time()), "data": [
            {"b64_json": res["b64"], "format": res.get("format", "mp4"),
             "note": res.get("note", "clip is ~10 seconds; request more for longer sequences")}]})

    def _handle_batch(self, body):
        tasks = body.get("tasks")
        if not isinstance(tasks, list) or not tasks:
            return self._err(400, '"tasks" must be a non-empty array')
        bid = "batch_" + secrets.token_hex(6)
        tids = []
        for t in tasks:
            kind = t.get("kind", "chat")
            if kind == "chat":
                payload = {"messages": t.get("messages", []), "model": "muse-bridge"}
            elif kind in ("image", "video"):
                payload = {"prompt": t.get("prompt", "")}
            elif kind == "audio":
                payload = {"input": t.get("input", "")}
            else:
                return self._err(400, "unknown task kind: %s" % kind)
            tids.append(new_task(kind, payload, batch_id=bid))
        _, color, _ = risk_of("batch")
        log_action("batch_queued", bid, "batch", "%d tasks" % len(tids), "queued")
        note("%sbatch %s queued%s (%d tasks)" % (color, bid, RESET, len(tids)))
        return self._send_json(200, {"id": bid, "status": "queued", "task_ids": tids})


def _refresher():
    while True:
        time.sleep(30)
        draw()  # keep ages/counts fresh between events (no-op w/o console)
        if _tray_icon is not None:
            _tray_icon.refresh_tip()  # tooltip carries version + live counts


# ---------------- task-tray mode (Windows, stdlib ctypes only) ----------------
# `python muse_bridge.py --tray`: hides the dashboard console and parks an icon
# by the clock. Right-click: live queue counts, show/hide the console, quit.
# Double-click: toggle the console. Task completions pop a notification.
# Launched with pythonw.exe there is no console at all -- tray becomes the UI.
# Any failure here falls back to plain console mode; the bridge keeps running.

_tray_icon = None


def tray_notify(title, text):
    """Balloon notification. No-op unless tray mode is up."""
    try:
        if _tray_icon is not None:
            _tray_icon.notify(title, text)
    except Exception:
        pass


def queue_counts():
    with TASKS_LOCK:
        queued = sum(1 for t in TASKS.values() if t["result"] is None)
        done = sum(1 for t in TASKS.values() if t["result"] is not None)
    return queued, done


class _TrayIcon:
    WM_TRAY = 0x0400 + 100
    NIM_ADD, NIM_MODIFY, NIM_DELETE = 0, 1, 2
    NIF_MESSAGE, NIF_ICON, NIF_TIP, NIF_INFO = 0x1, 0x2, 0x4, 0x10

    def __init__(self):
        import ctypes
        from ctypes import wintypes
        if sys.platform != "win32":
            raise RuntimeError("tray mode is Windows-only")
        self._ct = ctypes
        self._wt = wintypes
        # wintypes omits LRESULT on some builds (and WPARAM/LPARAM are not
        # guaranteed either); the Win32 message-proc types are just
        # pointer-sized ints, so define the trio locally and be done.
        self._LRESULT = ctypes.c_ssize_t    # LONG_PTR, signed
        self._WPARAM = ctypes.c_size_t      # UINT_PTR
        self._LPARAM = ctypes.c_ssize_t    # LONG_PTR
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self.kernel32 = ctypes.windll.kernel32
        self.gdi32 = ctypes.windll.gdi32
        # Correct prototypes for every handle-taking call. Without argtypes,
        # 64-bit handles are truncated to 32 bits -- that silently broke
        # CreateWindowExW (HWND_MESSAGE -3 arrived as 0xFFFFFFFF) and would
        # corrupt every icon/bitmap handle the same way.
        u32, k32, s32, g32 = self.user32, self.kernel32, self.shell32, self.gdi32
        k32.GetConsoleWindow.restype = wintypes.HWND
        k32.GetModuleHandleW.restype = wintypes.HMODULE
        k32.GetLastError.restype = wintypes.DWORD
        s32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.c_void_p]
        s32.Shell_NotifyIconW.restype = wintypes.BOOL
        u32.ShowWindow.argtypes = [wintypes.HWND, wintypes.INT]
        u32.ShowWindow.restype = wintypes.BOOL
        u32.IsWindowVisible.argtypes = [wintypes.HWND]
        u32.IsWindowVisible.restype = wintypes.BOOL
        u32.SetForegroundWindow.argtypes = [wintypes.HWND]
        u32.SetForegroundWindow.restype = wintypes.BOOL
        u32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT,
                                       self._WPARAM, self._LPARAM]
        u32.DefWindowProcW.restype = self._LRESULT
        u32.GetMessageW.argtypes = [ctypes.c_void_p, wintypes.HWND,
                                    wintypes.UINT, wintypes.UINT]
        u32.GetMessageW.restype = wintypes.BOOL
        u32.TranslateMessage.argtypes = [ctypes.c_void_p]
        u32.DispatchMessageW.argtypes = [ctypes.c_void_p]
        u32.GetDC.argtypes = [wintypes.HWND]
        u32.GetDC.restype = wintypes.HDC
        u32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
        u32.LoadIconW.argtypes = [wintypes.HINSTANCE, wintypes.LPCWSTR]
        u32.LoadIconW.restype = wintypes.HICON
        u32.CreateIconIndirect.argtypes = [ctypes.c_void_p]
        u32.CreateIconIndirect.restype = wintypes.HICON
        u32.CreatePopupMenu.restype = wintypes.HMENU
        u32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT,
                                    ctypes.c_void_p, wintypes.LPCWSTR]
        u32.AppendMenuW.restype = wintypes.BOOL
        u32.GetCursorPos.argtypes = [ctypes.c_void_p]
        u32.TrackPopupMenu.argtypes = [wintypes.HMENU, wintypes.UINT,
                                       wintypes.INT, wintypes.INT, wintypes.INT,
                                       wintypes.HWND, ctypes.c_void_p]
        u32.TrackPopupMenu.restype = wintypes.UINT
        u32.DestroyMenu.argtypes = [wintypes.HMENU]
        g32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, wintypes.INT,
                                               wintypes.INT]
        g32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
        g32.SetBitmapBits.argtypes = [wintypes.HBITMAP, wintypes.UINT,
                                      wintypes.LPVOID]
        g32.CreateBitmap.argtypes = [wintypes.INT, wintypes.INT, wintypes.UINT,
                                     wintypes.UINT, wintypes.LPVOID]
        g32.CreateBitmap.restype = wintypes.HBITMAP
        self.console = k32.GetConsoleWindow()  # NULL under pythonw
        self._tip = self._tip_text(0, 0)
        # The message window is created on the tray thread itself: window
        # messages are dispatched to the thread that created the window, so
        # building it on the main thread would leave clicks unhandled.
        self._ready = threading.Event()
        self._error = None
        self.hwnd = None
        self.icon = None

    def start(self):
        """Build the window + tray icon on the pump thread. Raises loudly."""
        threading.Thread(target=self._thread_main, daemon=True,
                         name="tray").start()
        if not self._ready.wait(timeout=15):
            raise RuntimeError("tray thread did not come up within 15s")
        if self._error:
            raise RuntimeError(self._error)

    def _thread_main(self):
        try:
            self._make_window()
            self.icon = self._make_icon()
            if not self._shell_notify(
                    self.NIM_ADD,
                    self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP):
                raise RuntimeError("Shell_NotifyIcon(NIM_ADD) failed, err=%d"
                                   % self.kernel32.GetLastError())
        except Exception as exc:  # noqa: BLE001 -- captured, re-raised by start()
            self._error = "%s: %s" % (type(exc).__name__, exc)
        finally:
            self._ready.set()
        if not self._error:
            self.run()  # message loop, forever

    # ----- hidden message window -----
    def _make_window(self):
        ctypes, wintypes = self._ct, self._wt
        WNDPROC = ctypes.WINFUNCTYPE(self._LRESULT, wintypes.HWND,
                                     wintypes.UINT, self._WPARAM,
                                     self._LPARAM)

        class WNDCLASSEXW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.UINT), ("style", wintypes.UINT),
                        ("lpfnWndProc", WNDPROC), ("cbClsExtra", ctypes.c_int),
                        ("cbWndExtra", ctypes.c_int),
                        ("hInstance", wintypes.HINSTANCE),
                        ("hIcon", wintypes.HICON), ("hCursor", wintypes.HCURSOR),
                        ("hbrBackground", wintypes.HBRUSH),
                        ("lpszMenuName", wintypes.LPCWSTR),
                        ("lpszClassName", wintypes.LPCWSTR),
                        ("hIconSm", wintypes.HICON)]

        def wndproc(hwnd, msg, wp, lp):
            if msg == self.WM_TRAY:
                if lp == 0x0205:        # WM_RBUTTONUP
                    self._popup()
                elif lp == 0x0203:     # WM_LBUTTONDBLCLK
                    self._toggle_console()
                return 0
            return self.user32.DefWindowProcW(hwnd, msg, wp, lp)

        self._wndproc = WNDPROC(wndproc)  # keep a ref: Windows calls back into it
        self.user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
        self.user32.RegisterClassExW.restype = wintypes.ATOM
        self.user32.CreateWindowExW.argtypes = [
            wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
            wintypes.INT, wintypes.INT, wintypes.INT, wintypes.INT,
            wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID]
        self.user32.CreateWindowExW.restype = wintypes.HWND
        wcx = WNDCLASSEXW()
        wcx.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wcx.lpfnWndProc = self._wndproc
        wcx.hInstance = self.kernel32.GetModuleHandleW(None)
        wcx.lpszClassName = "MuseBridgeTray"
        if not self.user32.RegisterClassExW(ctypes.byref(wcx)):
            raise RuntimeError("RegisterClassEx failed, err=%d"
                               % self.kernel32.GetLastError())
        self.hwnd = self.user32.CreateWindowExW(
            0, "MuseBridgeTray", "Muse Bridge Tray", 0,
            0, 0, 0, 0, -3, None, wcx.hInstance, None)  # -3 = HWND_MESSAGE
        if not self.hwnd:
            raise RuntimeError("CreateWindowEx failed, err=%d"
                               % self.kernel32.GetLastError())

    # ----- icon: teal circle, drawn by hand so there is no asset file -----
    def _make_icon(self):
        ctypes, wintypes = self._ct, self._wt
        W = H = 32
        xor = bytearray(W * H * 4)
        for y in range(H):
            for x in range(W):
                dx, dy = x - 16, y - 16
                if dx * dx + dy * dy <= 13 * 13:
                    i = (y * W + x) * 4
                    xor[i:i + 4] = b"\x33\xc4\x8a\x00"  # BGRA teal
        and_mask = bytes(W * H // 8)  # all zeros = fully opaque

        class ICONINFO(ctypes.Structure):
            _fields_ = [("fIcon", wintypes.BOOL),
                        ("xHotspot", wintypes.DWORD),
                        ("yHotspot", wintypes.DWORD),
                        ("hbmMask", wintypes.HBITMAP),
                        ("hbmColor", wintypes.HBITMAP)]

        hdc = self.user32.GetDC(None)
        try:
            hbm_color = self.gdi32.CreateCompatibleBitmap(hdc, W, H)
            if hbm_color:
                self.gdi32.SetBitmapBits(hbm_color, len(xor), bytes(xor))
            hbm_mask = self.gdi32.CreateBitmap(W, H, 1, 1, and_mask)
            hicon = None
            if hbm_color and hbm_mask:
                ii = ICONINFO(True, 0, 0, hbm_mask, hbm_color)
                hicon = self.user32.CreateIconIndirect(ctypes.byref(ii))
        finally:
            self.user32.ReleaseDC(None, hdc)
        if not hicon:
            # IDI_APPLICATION as MAKEINTRESOURCE (int-as-pointer, not a string)
            hicon = self.user32.LoadIconW(
                None, ctypes.cast(32512, wintypes.LPCWSTR))
        return hicon

    # ----- Shell_NotifyIcon wrapper -----
    def _shell_notify(self, nim, flags, info="", info_title="", info_flags=0):
        ctypes, wintypes = self._ct, self._wt

        class NOTIFYICONDATAW(ctypes.Structure):
            _fields_ = [("cbSize", wintypes.DWORD), ("hWnd", wintypes.HWND),
                        ("uID", wintypes.UINT), ("uFlags", wintypes.UINT),
                        ("uCallbackMessage", wintypes.UINT),
                        ("hIcon", wintypes.HICON),
                        ("szTip", wintypes.WCHAR * 128),
                        ("dwState", wintypes.DWORD),
                        ("dwStateMask", wintypes.DWORD),
                        ("szInfo", wintypes.WCHAR * 256),
                        ("uTimeout", wintypes.UINT),
                        ("szInfoTitle", wintypes.WCHAR * 64),
                        ("dwInfoFlags", wintypes.DWORD),
                        ("guidItem", ctypes.c_byte * 16),
                        ("hBalloonIcon", wintypes.HICON)]

        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = flags
        nid.uCallbackMessage = self.WM_TRAY
        nid.hIcon = self.icon
        nid.szTip = self._tip
        nid.szInfo = info[:255]
        nid.szInfoTitle = info_title[:63]
        nid.dwInfoFlags = info_flags
        return bool(self.shell32.Shell_NotifyIconW(nim, ctypes.byref(nid)))

    def notify(self, title, text):
        self._shell_notify(self.NIM_MODIFY, self.NIF_INFO,
                           info=text, info_title=title, info_flags=0x1)

    @staticmethod
    def _tip_text(queued, done):
        return "Muse Bridge v%s -- %d queued, %d done" % (VERSION, queued, done)

    def refresh_tip(self):
        """Re-point the hover tooltip at live counts. Best-effort."""
        try:
            queued, done = queue_counts()
            self._tip = self._tip_text(queued, done)
            self._shell_notify(self.NIM_MODIFY, self.NIF_TIP)
        except Exception:
            pass

    # ----- console show/hide -----
    def _toggle_console(self):
        if not self.console:
            return
        if self.user32.IsWindowVisible(self.console):
            self.user32.ShowWindow(self.console, 0)       # SW_HIDE
        else:
            self.user32.ShowWindow(self.console, 5)      # SW_SHOW
            self.user32.SetForegroundWindow(self.console)

    # ----- right-click menu (rebuilt fresh every open) -----
    def _popup(self):
        ctypes, user32 = self._ct, self.user32
        MF_STRING, MF_GRAYED, MF_SEPARATOR = 0x0, 0x1, 0x800
        queued, done = queue_counts()
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, MF_STRING | MF_GRAYED, 0,
                           "Muse Bridge -- %d queued, %d done" % (queued, done))
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        if self.console:
            vis = user32.IsWindowVisible(self.console)
            user32.AppendMenuW(hmenu, MF_STRING, 10,
                               "Hide dashboard" if vis else "Show dashboard")
        else:
            user32.AppendMenuW(hmenu, MF_STRING | MF_GRAYED, 0,
                               "No console (running under pythonw)")
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, 20, "Quit Muse Bridge")
        pt = self._wt.POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        cmd = user32.TrackPopupMenu(hmenu, 0x100, pt.x, pt.y, 0,
                                    self.hwnd, None)     # 0x100 = TPM_RETURNCMD
        user32.DestroyMenu(hmenu)
        if cmd == 10:
            self._toggle_console()
        elif cmd == 20:
            self.quit()

    # ----- message loop + quit -----
    def run(self):
        ctypes = self._ct
        msg = self._wt.MSG()
        while self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            self.user32.TranslateMessage(ctypes.byref(msg))
            self.user32.DispatchMessageW(ctypes.byref(msg))

    def quit(self):
        try:
            self._shell_notify(self.NIM_DELETE, 0)
        finally:
            os._exit(0)


def tray_init():
    """Bring the tray icon up. Returns True when it is running."""
    global _tray_icon
    try:
        icon = _TrayIcon()
        icon.start()
    except Exception as exc:  # noqa: BLE001 -- tray is cosmetic, never fatal
        msg = "tray unavailable (%s) -- continuing with console" % exc
        say(msg)
        # the dashboard redraw wipes the console, so persist this where it
        # can be read afterwards: ~/.muse-bridge/actions.log
        log_action("tray", "", "tray", msg, "failed")
        return False
    _tray_icon = icon
    if not FIRST_RUN and icon.console:
        # Hide the dashboard console; first run stays visible so the two
        # secrets printed on screen can be copied.
        icon.user32.ShowWindow(icon.console, 0)
    msg = ("tray icon up (v%s) -- right-click for status, "
           "double-click toggles console" % VERSION)
    say(msg)
    log_action("tray", "", "tray", msg, "ok")
    return True


if __name__ == "__main__":
    if "--version" in sys.argv:
        say("muse_bridge.py v%s" % VERSION)
        sys.exit(0)
    if FIRST_RUN:
        if HAS_CONSOLE:
            print("=" * 70)
            print("FIRST RUN -- save these, they are shown only once here.")
            print("  LAN bearer key (local tools): %s" % CONFIG["lan_key"])
            print("  Queue path (tunnel, your agent's worker): /q/%s/" % CONFIG["cap"])
            print("  Stored in %s (mode 600)" % CONFIG_PATH)
            print("=" * 70)
            print("Starting dashboard in 5 seconds... (Ctrl+C the old window if needed)")
            time.sleep(5)
        else:
            # pythonw: nowhere to print -- pop the secrets once instead.
            # They are also stored in CONFIG_PATH either way.
            import ctypes as _mb_ct
            _mb_ct.windll.user32.MessageBoxW(
                None,
                "LAN bearer key (local tools):\n%s\n\n"
                "Queue path (tunnel, your agent's worker):\n/q/%s/\n\n"
                "Stored in %s"
                % (CONFIG["lan_key"], CONFIG["cap"], CONFIG_PATH),
                "Muse Bridge v%s -- first run, save these" % VERSION, 0x40)
    threading.Thread(target=_refresher, daemon=True).start()
    if TRAY_MODE:
        tray_init()
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), H)
    srv.daemon_threads = True
    draw()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        say("\nbye.")
