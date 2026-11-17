# Muse Bridge as a Claude Code worker: setup and trial

**For the person:** paste this one line into Claude Code:

> Read https://github.com/BrentCrude79/muse-bridge/blob/main/CLAUDE-CODE-SETUP.md and follow it to add Muse Bridge as a worker, test it, and tell me what to use it for.

**For Claude Code:** the rest of this page is your runbook. Work through the steps in order. Ask the person only at the points marked **ASK**.

---

## 0. What you're connecting to

Muse Bridge puts an OpenAI-shaped front door and a task queue in front of the person's
**Muse agent** (Meta's Muse Spark). The Muse agent is a full agent, with web access, files and memory. It is
**not** a model endpoint. Here's how a task travels:

```
Claude Code ─MCP/HTTP─▶ bridge (/v1/*, LAN key) ─queue─▶ tunnel ─▶ Muse agent polls ~5 min
     ▲                                                                      │
     └──────────────────── result posted back to the queue ◀────────────────┘
```

Three facts shape everything below:

- **It's asynchronous.** A task waits for the agent's next poll (about every 5 minutes), then takes
  seconds to minutes to run. A reference trial took about 4–5 minutes end to end for each chat task. Nothing streams.
- **It's a queue.** A call holds the connection open for up to 15 minutes, then returns **504**. The task
  is **still queued**: poll `GET /v1/tasks/<id>`. A 504 isn't a failure. Tasks submitted together are
  picked up together on one poll. The queue lives in memory, so a bridge restart drops anything still queued.
- **Prompts go to Meta's service.** Never send secrets, keys, credentials, personal data, or code
  the person hasn't cleared to leave their machines. Use public or throwaway material.

## 1. Find or start the bridge

**ASK** the person:

1. Do you use Muse (meta.ai / the Muse app), and is a Muse Bridge already running? If so, where: on this
   machine, or on another one (a server, a NAS)?
2. If none is running: should it run on this machine, or on a Linux server with Podman?

Then:

- **Already running on this machine:** `~/.muse-bridge/config.json` exists and the bridge answers
  on `http://127.0.0.1:8472`. Go to step 2.
- **Running on another machine:** you need its URL and its **LAN key**, the `lan_key` field in that
  machine's `~/.muse-bridge/config.json`. Reach it over a private network: a tailnet
  `tailscale serve`, or an SSH port-forward. Never put `/v1` on the public internet.
  Write `~/.muse-bridge/mcp.json` on this machine:
  `{"base_url": "https://<host>:8472", "lan_key": "<key>"}`. Keep it readable by the person only
  (`chmod 600`, or an `icacls` grant on Windows). **Never print the key** in chat or logs.
- **Not running yet:** clone the repo and follow [`SETUP.md`](SETUP.md). On Windows, run the exe or
  `pythonw muse_bridge.py --tray`. On a Linux server, use the Podman quadlet in `deploy/podman/`. The first run creates
  the LAN key and the queue cap path. Then the person must:
  - expose **only** the queue paths to the internet (`tailscale funnel --set-path /q/<cap> ...`,
    or Cloudflare Tunnel with a path rule). See SETUP.md, step 2.
  - tell their Muse agent: *"queue is up at `<tunnel-url>` with cap path `/q/<cap>/`"*. **ASK** them
    to do this and tell you when it's done. You can't message Muse yourself.

## 2. Install the MCP server

```bash
git clone https://github.com/BrentCrude79/muse-bridge.git ~/muse-bridge   # or any folder
claude mcp add --scope user muse-bridge -- <python> ~/muse-bridge/muse_bridge_mcp.py
claude mcp get muse-bridge        # expect: Connected
```

- `<python>` is a full path to Python 3.9 or later (`python3` on macOS/Linux; on Windows, `where python`).
  The MCP server uses only the standard library.
- It reads `~/.muse-bridge/config.json` (a local bridge), then `mcp.json` (a remote bridge), then the
  `MUSE_BRIDGE_URL` and `MUSE_BRIDGE_KEY` environment variables.
- The five tools appear after Claude Code restarts:
  - `muse_task {prompt, system?}`
  - `muse_image`, `muse_say`, `muse_video` (save media to `~/dev-fleet/out/`)
  - `muse_batch {tasks, wait?, timeout_s?}`

  To run the trial **in this session without restarting**, call the HTTP routes directly (step 3).

## 3. Health check

`GET <base>/v1/models` with `Authorization: Bearer <lan_key>` should return 200 and list the model
`muse-bridge`. Without the key it should return 401. If you get anything else, fix the setup before going on.

Direct routes (model `"muse-bridge"`, `stream:false`):

| Route | Use |
|---|---|
| `POST /v1/chat/completions {model, stream:false, messages}` | One task. Holds open for up to 15 minutes. |
| `POST /v1/batches {tasks:[{kind:"chat", messages:[...]}, ...]}` | Returns `{id, task_ids}` immediately. |
| `GET /v1/batches/<id>`, `GET /v1/tasks/<id>` | Poll status and results. |

## 4. Trial: four jobs

**ASK** first: *"I'll send four small test tasks to your Muse agent. They're all public or throwaway
content, and they use a little of your Muse allowance. OK?"*

Submit all four together, then poll every 15–30 s **in the background**. Don't block your other work on
it. For each task, record: submit time, time picked up (queued → claimed), time finished, number of polls, and errors.

| Job | Send | What you're checking | How to score |
|---|---|---|---|
| a. Ping | `Reply with the word: ONLINE` | Round trip and latency | Exact word; total time |
| b. Review | A throwaway ~50-line snippet **you write**, in the person's main language, with 2 planted bugs (e.g. off-by-one, an unchecked error). Ask for findings with line numbers and a failing input. Keep the answer key to yourself. | Bug-finding accuracy | Bugs found / 2; false positives; are the lines right? |
| c. Research | One real, **public** platform question from the person's work, asking it to cite the official docs. Write down your own expected answer first. | Accuracy and citations | Claims right / total; open at least 2 cited pages and check they say what's claimed |
| d. Batch | `POST /v1/batches` with 3 short public-docs questions (a spec, an API limit, a protocol detail). Don't wait for it. | Queueing and parallel pickup | Were all 3 claimed on the same poll? Were all 3 correct? |

Optional, if the person wants media: one `muse_image` or `/v1/images/generations` with a harmless
prompt.

If nothing has been picked up after 15 minutes, the agent isn't polling. Check the tunnel URL and
cap path the person gave Muse, and **ASK** them to check that the Muse worker is enabled.

## 5. Report and recommend

Give the person a short report:

1. **Setup:** where the bridge runs, how Claude Code reaches it, and whether the MCP server shows Connected.
2. **Results table:** one row per job, with latency to pickup, latency to done, correctness, and errors.
3. **Recommendation.** Use the rubric below, adjusted to what you actually measured. If the person's CLAUDE.md already
   routes work to other workers (subagents, other CLIs or models), say where Muse fits next to them.

| If the trial showed | Recommend Muse for |
|---|---|
| Research claims mostly right, with citations that check out | **Cited platform and API research**, with spot-checks |
| Batch tasks all picked up on one poll and all correct | **Overnight and background batches** (queue them in the evening, collect them in the morning) |
| Review found the planted bugs with few false positives | **Second-opinion reviews of public or non-sensitive code** only |
| Media round-trips worked | **Images, TTS and short video clips** |

Never recommend Muse for:
- private or proprietary code;
- anything with secrets or personal data;
- security sign-off;
- tight edit and test loops;
- anything on the critical path that can't wait 5–10 minutes.

4. **Proposed routing line.** Draft the line, but don't write it. Offer one or two lines the person could add to their CLAUDE.md,
   for example: *"Cited public research and overnight batches go to Muse (muse-bridge MCP, async,
   ~5 min per task). Never private code or secrets."* Add it only if the person says yes.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| 401 | Wrong LAN key. Re-copy `lan_key` from the bridge machine's `config.json`. |
| 504 after 15 min | Not an error: poll `GET /v1/tasks/<id>`. If tasks are never picked up, the agent isn't polling. |
| 502 worker error | The agent tried and failed. The message says why. |
| MCP tools missing | Restart Claude Code; check `claude mcp get muse-bridge`. |
| Tasks vanished | The bridge restarted, and the queue lives in memory. Resubmit. |
