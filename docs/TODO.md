# TODO — Labourious deferred backlog

This file lists everything we explicitly deferred while building the project.
Items are grouped by **what they unblock** (when picking the next one to do,
pick the lowest-numbered group whose top item has the highest leverage).

The "What works today" section at the top is the snapshot — anything **not**
listed there is either pending or unbuilt.

---

## What works today (snapshot — `5ec42275` + `5f45250d`)

✅ Backend
- 28-agent system-prompt library (`docs/prompts/`)
- 4 streaming adapter families: Anthropic, OpenAI-compat (14 providers),
  Cohere, Gemini — sharing `runtime.adapters._streaming.StreamChunk`
- `call_agent(stream_chunks=…)` → one `AgentChunk` per text delta
- `execute_flow_f1(stream_chunks=…)` + `run_flow_stream(stream_chunks=…)`
  thread `stream_chunks` through every layer
- Cost tables per model family (Opus/Sonnet/Haiku, command-r-plus, gemini-2.5-pro/flash, …)
- Keychain-first auth (OS keychain → env → legacy fallback) across all adapters
- Mock runtime for deterministic pilots + offline demos

✅ Frontend
- Textual TUI: chat, sidebar, citation/history/help/citation-polish/settings modals
- Settings modal: 7 sections — providers / default / per-agent / hybrid /
  connectors / defaults / **streaming** (chunks toggle + typewriter_ms)
- Inline-edit rows (text + toggle) with per-row validation
- Inline editor commits via Enter / Tab + 1/2 shortcuts; reverts via Esc
- Chips filter (All / Free / Local / Paid / Custom) on the Providers panel
- Footer strip surfaces every binding per screen; Help modal cross-references them

✅ Process
- 22 pilots × ~394 individual tests, ZERO failures
- Direct CLI for both modes (`--dry-run` + real f1 flow)
- `run_flow_stream` end-to-end (`python docs/runtime/runtime.py --flow f1 --ticker NVDA`)

---

## Deferred — install & launch (next obvious move)

### [install-1] Real `pip install labourious` + install docs
- `pyproject.toml` (or `setup.py`) + package layout in `labourious/`
- Pin Python ≥ 3.11, deps: `textual`, `httpx`, `httpx_sse`, `keyring`, `pytest`
- Optional deps: `[secure]` for `keyrings.alt.file`, `[all]` for providers'
  native SDKs (`anthropic`, `openai`, `cohere`, `google-generativeai`)
- A README install section + `man` page or `--help` tour
- Smoke test on a clean machine: `pip install labourious && labourious`
- Blocked-by: nothing — purely packaging.
- Effort: medium (1 day, mostly testing pip-install paths across OS).

### [install-2] `python -m labourious` + `labourious` console script
- After `pip install -e .`, the user gets a single binary they can run anywhere
- Sets up `~/.labourious/` on first run with template config + welcome card
- Smoke: `pipx install .` produces a working global install
- Blocked-by: install-1.

---

## Deferred — first real Wharton memo end-to-end

### [domain-1] Run f1 against a real provider (not Mock, not MockTransport)
- Bring up Ollama locally (`ollama pull llama3.3:70b`) — easiest path
- Or: a free Gemini key + `gemini-2.0-flash` for a fast demo
- Or: OpenRouter-free models — one API key gives us ~50 free models
- Verify: every agent's envelope parses, agent emissions pass `validate_envelope`,
  citations resolve to real URLs, no fallback to Mock at runtime
- Blocked-by: a real key in keychain (the providers section + keychain
  UI is fully wired but we need a real key).

### [domain-2] Smoke test for connector-layer endpoints (SEC EDGAR, FRED, …)
- The Settings → Connectors section renders + saves, but `runtime/tools/`
  shells are stubs: hitting EDGAR for the actual 10-K text, FRED for DFF,
  Polygon for quotes, etc.
- Without this, SEC-derived citations are backfilled by the LLM
  (still useful, but unverified)
- Effort: medium (each connector is roughly 50 LOC + a keychain entry).

### [domain-3] Citation chip click → open source
- Today's chip is a count badge. Click should open the URL in OS browser
  AND fetch the snippet from the cited page so a reviewer can verify it.
- Or: open `less`/`bat` against the cached snippet file written on first read.
- Effort: medium.

---

## Deferred — protocol + polish

### [protocol-1] Live provider health probes
- The Settings panel shows a dot per-provider computed at startup
- Add a `↻ test` button next to each row → ping endpoint, report latency
- Free-tier providers (Cohere, Gemini, OpenRouter) benefit most

### [protocol-2] History modal: cursor pagination + cross-flow filter
- Today history shows latest 1 entry deep; add `↑/↓` paging + filter input
- Wharton's iterative workflow (re-run with new params, compare theses)
  needs this to actually pay dividends

### [protocol-3] Diff panel: side-by-side delta visualisation
- Today the DiffPanel shows literal `OLD → NEW` lines
- Replace with structured diff (`{added, removed, modified}`
  grouped by section: thesis / bottom_line / verification)

### [protocol-4] Activity panel: ETA + cost-so-far
- We already have cumulative in/out/USD; show "≈$0.34 remaining" badge
  per agent, refresh each AgentFinished

### [protocol-5] `/stream on|off|80` chat command
- Toggle stream_chunks + typewriter_ms from the chat input palette
  without opening Settings
- Persistence → already wired via `reload_config_from_disk` after save;
  just route through the same setter used by chat reload

### [protocol-6] Document v1 prompt schema (`docs/V1-PROTOCOL.md`)
- PROSE for each agent's expected input/output JSON shape
  (currently scattered across runtime/validate_envelope and the prompts)
- Single source of truth for "what does a good envelope look like"

### [protocol-7] Document v1 connector schema (`docs/V1-CONNECTORS.md`)
- Same for tools — what params, what response, how citation metadata
  is extracted

---

## Deferred — runtime hardening

### [runtime-1] Pull upstream SDKs (`anthropic`, `openai`, `cohere`,
`google-generativeai`) as optional `[all]` extras
- Today: 4 streaming adapters all use `httpx` directly — no SDK layer
- Pro: zero dep bloat for the default install
- Con: when SDKs change their SSE framing, we have to track.

### [runtime-2] Axios-style retry+backoff for transient HTTP errors
- Today: `AdapterHTTPError(status=429)` propagates to a banner + FlowFailed
- Add: client-side cap at N retries with exponential backoff on 429/5xx,
  with a "should retry?" callback to skip billing-required failures

### [runtime-3] Provider latency budget
- Some Wharton memo flows can take 60+ seconds end-to-end. Today
  there's no total run timeout — a hung Groq call blocks the bubble.
- Add: per-agent `timeout_s` capability budget, with a clean FlowFailed
  if any agent exceeds it (vs. AgentFailed mid-flow which already works)

### [runtime-4] Resume flow on partial failure
- After a FlowFailed, the CLI prints partial_envelopes. Recovery
  would be: re-run with `--resume-from <agent-id>` and reuse the prior
  bottom_line/citations to skip the agents that already succeeded.
- Useful but not v1; lower priority.

### [runtime-5] Adapter unit benchmarks
- Each pilot prints total_tests but not wallclock per test.
- Add `pytest --durations=10` baseline; CI gates if a pilot slows
  by >2× from its baseline.

---

## Deferred — UX

### [ux-1] Welcome card: 1-screen config wizard for new users
- Today: settings panel shows empty `No providers configured` and redirects
  to the per-provider add row
- Tomorrow: on first run, a guided 3-step picker: provider → model →
  free/paid mode, with `Skip` for "I'll come back to this"

### [ux-2] Footer hint redesign: surface the F1 flow's expected cost
- Today's footer hint shows model + depth + compressed + paid-for
- Add: "≈ $0.32 / run · 5 agents" based on per-model rate tables

### [ux-3] TUI on macOS / Windows parity
- We test on macOS via the desktop HTML preview. Windows keyboard
  navigation (alt-key bindings) and Linux colour-palette quirks
  need explicit verification.

### [ux-4] Auto-shrink bubbles when no model is loaded
- Today an empty bubble body prints `(run the flagship flow on a ticker to begin)`
  That's fine but a tiny "shortcut chips" row would help new users:
  `[NVDA] [AAPL] [MSFT] [GOOG] [TSLA]` selects a one-click ticker

---

## How to pick the next one

When picking what to do next, prefer the **top-most unfinished item** in the
list above. Items are ordered roughly by:

1. Install/packaging — unblocks every other user-tested feature
2. First real Wharton memo — proves the core thesis
3. Real connector data — closes the citation-verification loop
4. Protocol polish — improves UX without changing capability
5. Runtime hardening — adds robustness without capability

If a future task adds something to the **What works today** snapshot, update
this file in the same commit as the code change, so the snapshot stays
current.
