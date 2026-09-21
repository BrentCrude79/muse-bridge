## Why Muse Bridge?

Meta's **Muse Spark 1.3** creates an unusual situation in the current AI market: a frontier-class model paired with extraordinarily large consumer token allowances, but without a general-purpose endpoint that lets users spend those included tokens through the AI software ecosystem they already use.

Spark itself is not the limitation. Meta designed Spark 1.3 for reasoning, coding, tool use, long-context work, and agentic workflows. The problem is the interface between **the tokens Meta gives Muse users** and **the applications in which users might want to spend them**.

That gap is what Muse Bridge is intended to address.

### Muse Spark 1.3 is a frontier model

Meta positions Muse Spark 1.3 as a multimodal reasoning model designed for coding and agentic workloads, with text, image, and video capabilities and a context window of approximately **one million tokens**. See [Meta's Spark 1.3 announcement](https://research.meta.ai/blog/introducing-muse-spark-1-3) and the [Artificial Analysis model specifications](https://artificialanalysis.ai/models/muse-spark-1-3).

Independent evaluation by **Artificial Analysis** likewise places Spark 1.3 among contemporary high-end models, including systems from Anthropic and OpenAI. Its evaluations are particularly relevant here because they include coding and agentic benchmarks rather than measuring only conversational performance.

![Artificial Analysis comparison: Muse Spark 1.3 (max) alongside contemporary Claude, GPT, and other models](assets/muse-spark-artificial-analysis.png)

*Source: [Artificial Analysis — Muse Spark 1.3 model evaluation and Intelligence Index](https://artificialanalysis.ai/models/muse-spark-1-3). User-supplied comparison snapshot; rankings depend on model version and reasoning setting.*

The important point for Muse Bridge is not that Spark wins every benchmark. It doesn't. It is that the model being made available at this scale is sufficiently capable to be useful for exactly the kinds of **coding, automation, tool-use, and agent workloads** normally associated with expensive frontier-model inference.

### 100 million tokens per week — for free

Mark Zuckerberg has publicly described Meta's goal as making personal superintelligence broadly available, and announced that Muse users would receive up to **100 million tokens per week for free**. See [Meta's Muse launch announcement](https://about.fb.com/news/2026/09/introducing-muse-personal-ai-agent/).

That number becomes more striking when expressed on the same monthly basis normally used to price AI subscriptions.

Using 52 weeks ÷ 12 months:

| Muse plan | Tokens/week | Approx. tokens/month | Subscription |
| --- | ---: | ---: | ---: |
| **Muse Free** | 100M | **433M** | **$0** |
| **Muse Power** | 500M | **2.17B** | **$16/mo** |
| **Muse Maximum** | 3B | **13.0B** | **$80/mo** |

The free allocation alone therefore represents approximately **5.2 billion tokens per year** of potential model usage.

Power raises that to approximately **26 billion tokens per year**.

Maximum raises it to approximately **156 billion tokens per year**.

### Put that next to Claude Pro

Anthropic does not advertise Claude Pro as providing a fixed number of tokens. Its limits depend on usage patterns, model, context, and Anthropic's rolling usage windows.

For a concrete real-world comparison, however, the author of this project has observed approximately **200 million tokens per week of usable Claude Pro capacity** during heavy coding and agent usage.

That is an observed figure, **not an official Anthropic token entitlement**.

At 200M/week, a $20 Claude Pro subscription corresponds to approximately:

**867 million tokens/month.**

That gives us a useful practical baseline:

| Service | Approx. tokens/month | Monthly price | Relative to observed Claude Pro |
| --- | ---: | ---: | ---: |
| **Muse Free** | **433M** | **$0** | **0.5×** |
| **Claude Pro¹** | **867M** | **$20** | **1×** |
| **Muse Power** | **2.17B** | **$16** | **2.5×** |
| **Muse Maximum** | **13.0B** | **$80** | **15×** |

¹ *The Claude figure is the project author's observed usable capacity, not an Anthropic-advertised quota.*

On this real-world comparison, **Muse Power provides approximately 2.5 times the monthly tokens observed from Claude Pro while costing $4 less per month.**

Muse Maximum provides approximately **15 times the monthly token quantity for four times the subscription cost.**

Measured as tokens per subscription dollar:

| Service | Tokens/month | Price | Approx. tokens per $1 |
| --- | ---: | ---: | ---: |
| **Claude Pro¹** | 867M | $20 | **43.3M/$** |
| **Muse Power** | 2.17B | $16 | **135.4M/$** |
| **Muse Maximum** | 13.0B | $80 | **162.5M/$** |

That makes Power approximately **3.1× the observed Claude tokens per dollar**, while Maximum is approximately **3.75×**.

And Muse Free supplies approximately **half of the author's observed Claude Pro monthly capacity for $0**.

These figures compare **token quantity**, not absolute model capability. Tokens produced by different models are not intrinsically equivalent units of intelligence, latency, compute, or useful work.

### Another way to look at the numbers: $0.10 per million tokens

There is also a useful external reference point for what extremely inexpensive Spark inference looks like.

The project author's OpenCode Zen / Muse Spark Contributor comparison uses **$0.10 per million input tokens** and **$0.20 per million output tokens** as its reference rates. The Contributor program achieves those unusually low prices in exchange for permission to use prompts and completions for model training. See [OpenCode Zen](https://dev.opencode.ai/docs/zen).

Using the **$0.10/M input-token figure** as a deliberately simple common denominator, the raw token quantities represented by the Muse subscriptions become:

| Muse plan | Approx. tokens/month | At $0.10 / 1M tokens | Subscription |
| --- | ---: | ---: | ---: |
| **Free** | 433M | **$43.30** | **$0** |
| **Power** | 2.17B | **$217** | **$16** |
| **Maximum** | 13.0B | **$1,300** | **$80** |

This is intentionally an **input-token-equivalent calculation using the $0.10/M figure**, not an estimate of Meta's cost of serving Muse and not a claim that every Muse token would otherwise cost exactly ten cents per million.

It provides a common denominator for understanding the sheer quantity of inference represented by the allocations.

At even that extremely inexpensive reference price, the **$16 Power subscription contains a nominal token quantity equivalent to roughly $217/month of $0.10/M inference**, while the **$80 Maximum subscription represents roughly $1,300/month**.

### So why not just connect Muse to your existing tools?

Because the enormous consumer allocation and the general-purpose developer interface are two different products.

Spark 1.3 itself is explicitly capable of coding and agentic work. Meta also provides **Muse Code**, giving Spark a first-party coding environment.

But Muse Code does **not** give a free Muse user a general-purpose OpenAI-compatible API endpoint representing that user's included **100M tokens/week**.

That distinction is critical.

The modern AI ecosystem increasingly depends on standardized inference interfaces. An OpenAI-compatible endpoint can be consumed by or adapted into tools such as:

- SillyTavern
- Open WebUI
- local-LLM front ends
- agent frameworks
- orchestration systems
- API routers
- automation platforms
- development environments
- countless applications already built around OpenAI-compatible APIs

Claude Code uses Anthropic's protocol rather than the OpenAI Chat Completions protocol directly, but the same architectural issue applies: connecting an arbitrary model requires an appropriate endpoint or compatibility layer.

**Muse's free consumer allowance provides neither an unrestricted OpenAI-compatible endpoint nor a generic API balance that can simply be dropped into those applications.**

Muse Code addresses coding by supplying **Meta's coding harness**.

It does not expose the user's consumer Muse allocation as a general-purpose inference service for arbitrary third-party software.

### Spark is available by API — but that is a different pool of tokens

This distinction is easy to miss because Muse Spark **is** available through APIs.

For example, OpenCode Zen currently exposes regular Muse Spark 1.3 through an OpenAI Responses-compatible interface, and separately exposes Muse Spark 1.3 Contributor. OpenCode's published pricing currently lists regular Spark at **$1.25/M input and $4.25/M output**, while its Contributor offering can be dramatically cheaper or temporarily free under different conditions. See [OpenCode Zen's model interfaces and pricing](https://dev.opencode.ai/docs/zen).

That proves the underlying model can operate perfectly well behind a standardized inference interface.

What it does **not** do is turn:

**your 100M/week free Muse allowance**

into:

**your 100M/week OpenAI-compatible API allowance.**

Those are separate access paths.

And that distinction becomes increasingly significant at the paid consumer tiers, where the allocation grows from hundreds of millions into **billions of tokens per week**.

### The interface gap

That leaves an unusual mismatch:

> **Meta has made an enormous quantity of frontier-class inference available to individual users, but the largest subsidized allocation lives inside Meta's Muse ecosystem rather than behind the general-purpose inference interfaces used by much of the existing AI software ecosystem.**

Spark does not need Muse Bridge to become agentic.

Spark is already agentic.

It does not need Muse Bridge to become a coding model.

Meta already provides Muse Code.

**The missing piece is interoperability.**

Muse Bridge is designed to address that interface boundary: allowing existing AI applications, coding tools, agent frameworks, local-LLM software, and orchestration systems to work with Muse through familiar inference interfaces rather than requiring every application to understand a Meta-specific consumer harness.

**Meta supplied the model.**

**Meta supplied the tokens.**

**Muse Bridge supplies the bridge.**



Dispatch work to a full agent — not just a model — from any tool that speaks OpenAI.

This repo holds the bridge: a tiny Python front door that runs on your
workstation. Your local tools (Claude Code, Codex, opencode, OpenWebUI,
SillyTavern, curl, anything with a `base_url` + `api_key` + `model` field)
talk to it like it's an OpenAI-compatible API. Behind the front door is a task
queue, and behind the queue is your AI agent: a real agent with web access,
files, memory, and media generation. It picks tasks up through a tunnel, does
the work, and returns the answers.

The key idea: **latency is minutes, granularity is tasks.** This isn't for
tight autocomplete loops — it's for "research this," "generate that," "handle
these ten things overnight," dispatched from whatever tool you're already in.

```
your tools ──OpenAI-shaped──▶ Muse Bridge (127.0.0.1:8472) ──queue──▶ tunnel ──▶ your agent
   ▲                                                                               │
   └────────────── answers (chat / png / mp3 / mp4) ───────────────────────────────┘
```

![Live console dashboard](docs/dashboard.png)

*The live console: queue counters, live tasks with security color + latency
axis, and the recent-action log. The exe parks it by the clock — hover the
flower for the same counters in a tooltip.*

- **Chat** → research, writing, analysis, code review, second opinions
- **Images** → generated PNGs, base64 in an OpenAI-style response
- **Audio** → text-to-speech MP3s (voiceovers, read-aloud, narration)
- **Video** → ~10s MP4 clips from a text prompt (stitch for longer)
- **Batches** → queue N tasks in one call, collect results in the morning

**v1.0.** Chat + image round-trips verified end-to-end over a Tailscale
Funnel tunnel. One-file exe (`MuseBridge.exe`: bridge in tray mode + the
5-tool MCP server via `--mcp`). MCP toolset built and smoke-tested; awaiting
first live use. (Numbering note: the pre-release dev builds were numbered
2.0–2.10 during the build-out — retroactively they're 0.x. v1.0 is the first
real build.)

## Quickstart

Three steps (full guide in [`SETUP.md`](SETUP.md)):

1. **Get the exe** — download `MuseBridge-win-arm64.exe` from the
   [v1.0 release](../../releases/tag/v1.0) (prebuilt, Windows ARM64) and
   double-click it. (On x64 Windows, build it once instead — PyInstaller
   can't cross-build, not even across architectures; full notes in
   [`BUILD-EXE.md`](BUILD-EXE.md): `pip install pyinstaller`,
   `cd C:\Users\<you>\apps\muse`, `pyinstaller MuseBridge.spec`.)
   The flower parks by the clock — the bridge is up, in tray mode, no console. First run pops one
   dialog with two secrets, stored in
   `C:\Users\<you>\.muse-bridge\config.json`:
   - **LAN bearer key** → paste into your local tools. Model name: `muse-bridge`.
   - **Queue path** (`/q/<random>/`) → give to your agent with your tunnel URL.
     Never put it in a tool config; it's tunnel-only.
   (Rather run scripts? `pythonw.exe muse_bridge.py --tray` does the same —
   stdlib only, no packages.)
2. **Tunnel the queue paths only** (`/q/<cap>/pending`, `/q/<cap>/result/<id>`,
   `/q/<cap>/status`) — Tailscale Funnel or Cloudflare Tunnel. Never expose
   the whole port.
3. **Tell your agent** "queue is up at `<tunnel-url>` with cap path `/q/<...>/`"
   and it enables its worker (polls every ~5 min) plus an optional morning digest.
   Have it save the worker protocol — tunnel URL, cap path, the
   `pending?claim=1` / `result/{id}` endpoints, and the safety rules — to its
   long-term memory. Then any future session can run the worker without being
   briefed again.

## Connect your tools

Anything that can point at a custom OpenAI-compatible endpoint works. The
pattern is always the same: base URL `http://127.0.0.1:8472`, API key = your
LAN bearer key, model = `muse-bridge`.

| Tool | How | Status |
|------|-----|--------|
| **Claude Code** | MCP via the exe: `claude mcp add muse-bridge -- C:\Users\brent\apps\muse\MuseBridge.exe --mcp`. Five worker tools: `muse_task`, `muse_image`, `muse_say`, `muse_video`, `muse_batch`. Dispatch work like a subagent. | 🛠️ built, ready |
| **Codex** | MCP via the exe (`~/.codex/config.toml`, `mcp/configs/codex-config.toml`) — same five tools, headless dispatch from scripts. | 🛠️ built, ready |
| **opencode** | MCP via the exe (`opencode.json`, `mcp/configs/opencode.json`). | 🛠️ built, ready |
| **Cline** | MCP via the exe (`cline_mcp_settings.json`, `mcp/configs/cline_mcp_settings.json`). | 🛠️ built, ready |
| **goose** (Block) | MCP extension via the exe (`~/.config/goose/config.yaml`, `mcp/configs/goose-config.yaml`). | 🛠️ built, ready |
| **OpenWebUI** | Admin → Connections → add OpenAI API connection: base URL + key, model `muse-bridge`. Chat UI for the queue. | 🔶 expected |
| **SillyTavern** | API Connections → OpenAI-compatible: custom endpoint + key. Personas that can hand tasks to a real agent. | 🔶 expected |
| **Tavo** | Custom OpenAI-compatible provider (TTS/audio routes). | 🔶 expected |
| **zcode / hermes / ohmypi** | If it speaks OpenAI-style chat completions, it works — exact config TBD. PRs welcome. | 🔶 TBD |
| **curl / scripts** | Raw HTTP, OpenAI shapes. Great for cron jobs and pipelines. | ✅ verified live |

Legend: ✅ verified end-to-end · 🛠️ built, awaiting first use · 🔶 standard
OpenAI-compatible config, not yet tried — report back.

Full per-host MCP setup (all five hosts) in [`mcp/INSTALL.md`](mcp/INSTALL.md);
copy-paste configs live in `mcp/configs/`.

## Run it

The exe is the preferred way — one file, no console, tray-first.
Grab `MuseBridge-win-arm64.exe` from the [v1.0 release](../../releases/tag/v1.0)
(prebuilt), or build it yourself once (notes: [`BUILD-EXE.md`](BUILD-EXE.md)):

```bat
pip install pyinstaller
cd C:\Users\<you>\apps\muse
pyinstaller MuseBridge.spec     :: build once
```

Double-click the exe and the flower parks by the clock:
hover for the version and live queue counts, right-click for status or
quit, double-click toggles the console dashboard. Task completions pop a
notification. First run shows one dialog with the two secrets — save them.
`MuseBridge.exe --mcp` serves the five MCP tools over stdio for Claude
Code / Codex / opencode / Cline / goose. The exe reads the same
`~/.muse-bridge/config.json`, so keys carry over — and it's unsigned, so
SmartScreen asks once. Expected.

Prefer scripts? `pythonw.exe muse_bridge.py --tray` runs the same tray
mode (still stdlib-only: raw `ctypes`, the icon drawn in code, no
packages); `python muse_bridge_mcp.py` is the standalone MCP server. Any
tray failure falls back to the console with the reason in the action log.

## What you can do with it

### Via the OpenAI endpoint

**Research & knowledge work**
- Deep research questions from any chat UI — the agent browses the live web,
  reads sources, and returns a writeup
- Overnight research batches: queue 10 questions, read the digest in the morning
- Competitive teardowns, product comparisons, market scans
- "Explain this" — paste an error, a paper abstract, a contract clause

**Code-adjacent (from your editor/CLI agent)**
- Second-opinion code review: paste a diff, get a review from an agent with
  no stake in the code
- Documentation generation from source you paste in
- Commit messages, PR descriptions, changelogs, release notes
- Test data and fixtures, edge-case enumeration
- Architecture sanity checks ("here's my plan, poke holes in it")

**Writing & content**
- Drafts, rewrites, summaries, tone shifts
- Meeting notes → action items; long threads → briefings
- Morning briefing batch: "summarize X, Y, Z overnight"

**Media generation**
- Images: thumbnails, concept art, mockups, social assets (`1024x1024`,
  base64 PNG back)
- Audio: article narration, video voiceovers, read-aloud for long docs,
  podcast-style briefings
- Video: ~10s clips from a prompt — b-roll, animated logos, teasers
  (stitch clips for longer pieces)

**Pipelines & automation**
- Cron + curl: nightly repo digest, inbox triage drafts, changelog assembly
- Batch endpoint: one call queues chat/image/audio tasks together; poll or
  wait for the morning digest
- Home-lab glue: any script that can POST JSON can hire an agent for a step

### Via MCP (worker tools)

The MCP server treats the other end as a **colleague agent** inside your
coding tool — best when the task benefits from the agent's full context
(memory, files, web) rather than raw speed:

- `muse_task` — well-specified research, design docs, "second engineer"
  reviews, writing release notes, triaging issues. Not for tight
  edit/compile loops (minutes of latency).
- `muse_image` — concept art and assets saved straight to
  `~/dev-fleet/out/` on the workstation.
- `muse_say` — TTS MP3s to `~/dev-fleet/out/` — demo voiceovers,
  read-aloud reviews.
- `muse_video` — ~10s MP4 clips to `~/dev-fleet/out/` from a text prompt.
- `muse_batch` — queue several tasks at once and collect the results;
  `wait:false` returns the batch id immediately for later polling.

The same pattern generalizes: any MCP host can wrap the HTTP routes the way
`muse_bridge_mcp.py` does.

### Ideas not yet tried (filter freely)

- SillyTavern persona whose "actions" are queue dispatches — a character that
  can actually go do things and report back
- OpenWebUI pipeline that routes hard questions to the agent, easy ones local
- Voice assistant loop: TTS out + STT in, the agent in the middle, via batches
- Game NPC dialogue generation in bulk (one batch call, dozens of lines)
- CI job that has the agent summarize the nightly test failures in prose
- "Explain my own codebase to me" docs sprint: batch one task per module
- Accessibility: batch-convert a reading list to audio overnight
- Red-team: have the agent attack your plan while your local model defends it

## The console dashboard & local action log

The bridge window is a live dashboard: every queued task, its status, and
risk on two axes — **security as color** (🟢 LOW just making something for
you · 🟡 MEDIUM open-ended, review it · 🔴 HIGH many at once) and **latency
as a word** (FAST one worker cycle · MEDIUM generation takes minutes ·
SLOW video/batches, settle in). Files the worker reports touching are cited
under the task, with a review nudge when security isn't green. Every event also
appends to `~/.muse-bridge/actions.log` (JSONL) — written **only** by the
bridge process on your PC; the queue protocol has no route to read or change
it. Files the worker reports touching are logged as the worker's own claim.

## The mental model

| | Local model (Kobold, etc.) | Muse Bridge → agent |
|---|---|---|
| Latency | seconds | minutes |
| Best for | tight loops, autocomplete, chat | tasks, research, media, batches |
| Context | what you paste | its memory, files, web, tools |
| Cost | electricity | its worker schedule |

Use both. Fast local for the loop, the agent for the errands.

## Security design

This is the part we're proudest of: Muse Bridge is **one-way by
construction**. Your machines reach out; the agent only ever returns data.
There is no path — direct or creative — by which the agent (or anyone
holding its credentials) can execute code on your workstation. That's not
a limitation we worked around. It's the core security property of the
whole design.

**Three venues, three trust levels.** Chat sessions and the tunnel worker
live on the agent's machine: zero filesystem access to your PC, and the
bridge protocol exposes no file-write route — the queue surface is
`pending`, `result/{id}`, `status`, and that's everything. The bridge
server on your workstation stores results as inert data; nothing it
receives is evaluated or executed, because there is no command task kind.
The *only* thing on your machine that writes files is the MCP server
(`muse_bridge_mcp.py`), which runs locally **as you** and saves the
agent's media results to disk. The writer is your code, on your box,
under your user's hands.

**The narrowest possible blast radius.** The LAN bearer key never leaves
your machines (it gates `/v1/*`). The queue cap path (`/q/<random>/`) is
unguessable and tunnel-only — and even if it leaked, all it buys is a
task inbox: reading your queued tasks and posting bogus results. No
execution. No file writes. No reach into the dashboard or the local
action log (written solely by the bridge process; the queue protocol has
no route to either). The "files" a worker reports touching are logged as
its own unverified claim, and treated that way.

**The checklist:**

- The **LAN bearer key** never leaves your machines. It gates `/v1/*`.
- The **queue path** (`/q/<random>/`) is unguessable and tunnel-only. It is
  not a credential — don't put it in tool configs.
- The bridge binds `127.0.0.1` only. The tunnel exposes queue paths, never
  the whole port.
- Rotate keys by deleting `~/.muse-bridge/config.json` and restarting —
  both secrets regenerate. Then update your tools (and the agent's cap path).
- **Destructive actions ask first.** The worker answers and generates; it
  doesn't run irreversible operations without your confirmation.

## Limits, honestly stated

- **Latency is minutes, not seconds.** Worker polls every ~5 min; media takes
  minutes more. Task granularity, not tight loops.
- **No streaming** (`stream: false` only). The connection holds open up to
  15 min; after that, 504 — poll `GET /v1/tasks/<id>`.
- **Video**: ~10s clips, synthesized sound from a text mood description, no
  audio input.
- **Audio**: speech/TTS and podcast-style voices only. No song/music lookup.
- **Media returns base64** (~33% inflation). Keep video requests modest.
- **Server restarts wipe the in-memory queue.** For real durability, keep the
  bridge on a scheduled task / service.

## Files

- `MuseBridge.spec` + `muse-bridge.ico` + `BUILD-EXE.md` — build the
  one-file exe (`pyinstaller MuseBridge.spec` → `dist\MuseBridge.exe`).
  **This is the preferred way to run it.** Prebuilt binary
  (`MuseBridge-win-arm64.exe`, Windows ARM64) is attached to the
  [v1.0 release](../../releases/tag/v1.0).
- `muse_bridge.py` — the front door + queue + task-tray mode (workstation, stdlib only). `python muse_bridge.py --version` prints the build; the version also shows in the dashboard header and the tray tooltip, so you can tell a stale copy from a fresh one. `muse_bridge.py --mcp` runs the MCP server.
- `muse_bridge_mcp.py` — MCP server: 5 tools for Claude Code / Codex / opencode / Cline / goose (stdio, stdlib only). Also served from inside the exe.
- `mcp/INSTALL.md` — per-host MCP setup guide
- `mcp/configs/` — copy-paste configs: Codex (toml), opencode (json), Cline (json), goose (yaml)
- `SETUP.md` — full setup guide: tunnel options, tray mode, batches, troubleshooting

## Roadmap ideas

- Jev (TypeSafe.ai) judgement layer: offload worker decision-making — task
  triage, difficulty scoring, routing — to a judgement model instead of the
  worker's own heuristics
- Webhook callbacks instead of hold-open connections
- File download route (PDFs, zips) alongside base64 media
- Longer video via server-side clip stitching
- Persistent queue (sqlite) so restarts don't drop tasks
- Streaming for chat tasks

---

Built for one workstation and one agent, shared in case the pattern is useful.
Issues and integration notes (especially for the 🔶 rows) welcome.
