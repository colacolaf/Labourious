# SPEC — the app's layout, node types, panels, and interactions

> **Audience:** a developer implementing the app. The spec is for the **shape** of the app — what the user sees, what they can do, what happens. Implementation details (file plan, line budgets) are in [`IMPLEMENTATION.md`](IMPLEMENTATION.md); the runtime-side contract (graph JSON, WS events) is in [`PROTOCOL.md`](PROTOCOL.md).

**Stack:** Tauri 2 + React 18 + React Flow (xyflow) + Zustand. Bundled Python sidecar over a local WebSocket. See [`STACK-DECISION.md`](STACK-DECISION.md) for the research.

## 1. Top-level layout — three panes

```
┌────────────────────────────────────── desktop window ────────────────────────────────────┐
│ ┌── top bar (40px) ─────────────────────────────────────────────────────────────────────┐ │
│ │ Labourious · [● runtime: connected] · default: ollama/llama3.3:70b · [▶ Run] [⏹ Stop] │ │
│ └──────────────────────────────────────────────────────────────────────────────────────┘ │
│ ┌── left panel (280px) ──┐ ┌── canvas (flex) ───────────────────┐ ┌── right panel (420px)┐ │
│ │ ▼ Settings             │ │                                      │ │ ▼ Run: NVDA · f1-eq  │ │
│ │   Provider keys  [+]   │ │     ┌──────────┐    ┌──────────┐    │ │   ○ orchestrator 0.4s│ │
│ │   Default model  ▾     │ │     │ ① senior │───▶│ ③ forensic│    │ │   ● senior      ▒ 2.1s│ │
│ │   Depth          ▾     │ │     │ analyst  │    │   acct    │    │ │   ◐ forensic    ▒    │ │
│ │   Connectors     ⚙     │ │     └────┬─────┘    └──────────┘    │ │   … devils-adv     │ │
│ │ ▼ Agent Library        │ │          │                           │ │   … final-report   │ │
│ │   Built-ins (5)        │ │          ▼                           │ │ ───────────────────  │ │
│ │   ┌─────────────────┐  │ │     ┌──────────┐                      │ │ ▼ Memo (streaming)  │ │
│ │   │ Technical      │  │ │     │ ④ devil's│                      │ │ # Bottom line — HOLD│ │
│ │   │ drag to canvas │  │ │     │ advocate │                      │ │   (4/5)             │ │
│ │   └─────────────────┘  │ │     └────┬─────┘                      │ │ Wide-moat franchise │ │
│ │   ┌─────────────────┐  │ │          │                             │ │ at $890…            │ │
│ │   │ Quant           │  │ │          ▼                             │ │ ## Bull case …       │ │
│ │   └─────────────────┘  │ │     ┌──────────┐                      │ │ ## Bear case …       │ │
│ │   Macro · Flow+Trans  │ │     │ ⑤ final  │                      │ │ ## Citations [12]    │ │
│ │   Research-forcer ⚡   │ │     │ report   │                      │ │ ───────────────────  │ │
│ │ ▼ My Flows             │ │     └──────────┘                      │ │ Σ $0.00 · 5.2k in    │ │
│ │   📄 NVDA deep-dive    │ │                                      │ │     · 1.1k out       │ │
│ │   📄 semis compare     │ │   [zoom: 100%] [⌖ fit] [⊞ grid]       │ │                      │ │
│ │   + import flow file   │ │                                      │ │                      │ │
│ └───────────────────────┘ └──────────────────────────────────────┘ └─────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────────────────────┘
```

The layout is a three-column flex grid (`LeftPanel`, `Canvas`, `RightPanel`) under a 40px top bar. All panes are resizable via drag handles between them. The canvas takes the remaining width; left and right panels have sensible defaults (280px / 420px) and persist their width to `~/.labourious/config.json` under `app.ui` on resize.

---

## 2. Top bar

A single 40px bar across the top. Contents (left to right):

| Element | Behavior |
|---|---|
| **Logo + name** | "Labourious" — static. |
| **Runtime status** | `[● runtime: connected]` (green) / `[○ runtime: starting…]` (amber) / `[✗ runtime: disconnected]` (red). Click → opens runtime diagnostics modal. |
| **Default model** | Dropdown of available models (read from providers in `~/.labourious/config.json`). Selecting sets the global default for any node without an explicit override. |
| **▶ Run button** | Compiles the current graph + reads the ticker input + sends `run_flow` to the bridge. Disabled if graph is empty or has a cycle. Shows "▶ Run" when idle, "⏹ Stop" when running. |
| **⌘R / Ctrl+R** | Keyboard shortcut for Run. |
| **⌘S / Ctrl+S** | Save current graph to `~/.labourious/flows/`. |

---

## 3. Left panel — Settings + Agent Library + My Flows

A single scrollable panel with three collapsible sections.

### 3.1 Settings section

| Field | Type | Behavior |
|---|---|---|
| Provider keys | List of providers (Anthropic, Ollama, Groq, OpenRouter, OmniRoute, Google AI Studio) with a `[+]` add button. Each row: provider name, base_url (editable), API key field (password-masked), ↻ test button. | Reads/writes `~/.labourious/config.json` + OS keychain. The ↻ test calls the runtime's provider-health probe (same as TUI's Settings → Providers ↻). |
| Default model | Dropdown (e.g. `ollama/llama3.3:70b`, `anthropic/claude-sonnet-4-5`). | Sets the global default; per-node dropdowns override. |
| Depth | Dropdown: `SCAN` / `STANDARD` / `DEEP` / `COMPRESSED`. | Passed to `run_custom_flow_stream` as `depth`. |
| Connectors | Gear icon → opens a connectors modal (per-tool provider selection: `sec_edgar` keyless, `news` google_rss/newsapi, `market_data` yfinance+fred, `web_fetch` no-config). | Reads/writes the `connectors` block of `~/.labourious/config.json`. |
| Runtime | "Connect to existing runtime" toggle + URL field (default: bundled sidecar on `127.0.0.1:<auto-port>`). | Power-user override. |

### 3.2 Agent Library section

Two subsections:

- **Built-ins (5)** — orchestrator, senior-analyst, forensic-accounting, devil's-advocate, final-report. Always available; rendered as drag-source cards. Each card shows the agent name + a one-line description + a small icon.
- **Library** — the curated catalog (technical, quant, macro, flow-and-transcript, research-forcer). Rendered as drag-source cards with the same shape. The set is loaded from `app/agent-library/*.json` at startup; a "Refresh library" button reloads from disk.

Dragging any card onto the canvas creates a new node of that type at the drop position. The library panel does **not** show nodes already on the canvas (the canvas is the workspace; the library is the palette).

### 3.3 My Flows section

- A list of saved `.labourious-flow.json` files from `~/.labourious/flows/`. Each row: flow name, last-modified date, a small preview icon.
- Click → loads the graph into the canvas (replacing the current one, with a "unsaved changes" confirmation if dirty).
- `+ Import flow file` → opens a file picker to import an external `.labourious-flow.json`.
- Right-click a row → Rename / Duplicate / Delete.

---

## 4. Canvas — React Flow graph

The center workspace. A React Flow canvas with:

### 4.1 Node types

Each node is a rounded card with:
- **Header** — agent icon + name + model-dropdown (the per-node override; defaults to `[default]`).
- **Body** — runtime status indicator: `○ queued` / `◐ running` (with a small spinner) / `● done` (with wallclock) / `✗ failed` (with error). When idle, the body shows a one-line description of what the agent does.
- **Footer** — when the node has run: token counts (`in: 4.2k · out: 1.1k`), cost (`$0.00`), and a citation-count chip (`[12 citations]`) if applicable.
- **Input handle** (left edge) and **output handle** (right edge). A node can have multiple input handles (fan-in) and multiple output handles (fan-out).

**Built-in node types** (Phase 1):
- `orchestrator` — teal accent.
- `senior-analyst` — gold accent.
- `forensic-accounting` — blue accent.
- `devils-advocate` — red accent.
- `final-report` — green accent.

**Library node types** (Phase 3): `technical`, `quant`, `macro`, `flow-and-transcript`. Each follows the same shape; accent colors per the catalog JSON.

**Research-forcer node** (Phase 4): a special node with **no agent** — it's a directive-injector placed *on an edge* between two agents. Visually rendered as a small diamond-shaped badge on the edge, with a `depth_budget` number and an editable `directive_template` field. See [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md) §Research-forcer.

### 4.2 Edge types

- **Pass-through** (default) — the upstream agent's envelope flows to the downstream agent's brief unchanged.
- **Research-forcer** — a special edge with a diamond badge; on Run, the upstream agent re-runs with an injected "dig deeper" directive before the envelope flows downstream. See Phase 4 of [`ROADMAP.md`](ROADMAP.md).

### 4.3 Canvas interactions

| Action | Input |
|---|---|
| Pan | drag on empty canvas / two-finger trackpad / space+drag |
| Zoom | scroll / pinch / `+` / `-` / `⌘0` reset |
| Select node | click |
| Multi-select | shift+drag box / shift+click |
| Delete selected | `Delete` / `Backspace` |
| Duplicate selected | `⌘D` / `Ctrl+D` |
| Connect nodes | drag from output handle to input handle |
| Add node | drag from library panel / double-click empty canvas → node-type picker |
| Fit to view | `⌘F` / `Ctrl+F` / click `⌖ fit` button |
| Toggle grid | `⊞ grid` button |

### 4.4 Graph validation (pre-Run)

Before Run, the app validates the graph. Failures surface as a red banner above the canvas:

- **Cycle detected** — "Graph contains a cycle: A → B → A. Remove one edge to fix."
- **No terminal node** — "Graph has no final-report (or equivalent terminal) node. Add one to produce a memo."
- **Unconnected node** — "Node 'technical' is not connected. Remove it or wire it in." (warning, not blocker)
- **Missing ticker** — "Enter a ticker in the top bar or right panel before running."
- **Missing API key** — "No API key for {provider}. Add one in Settings → Providers."

---

## 5. Right panel — Run output + memo

The right panel is the output surface. Two collapsible sections.

### 5.1 Run activity section

- A header: "Run: {ticker} · {flow name or 'custom graph'}".
- A vertical list of agent rows (one per node in the graph that's run or is running), each:
  - State icon: `○` queued / `◐` running (with spinner) / `●` done / `✗` failed / `–` skipped.
  - Agent name + model shortname.
  - Wallclock (live while running; final when done).
  - Token counts (when done).
  - Cost (when done).
- A summary footer: `{N}/{M} done · Σ ${cost} · {wallclock}s`.
- This mirrors the TUI's `ActivityPanel` widget — same data, app-native rendering.

### 5.2 Memo section

- Streams the final memo as Markdown (`react-markdown`), section by section, as the `final-report` agent emits it.
- Sections render as cards:
  - **Bottom line** — direction + conviction (1–5) + flip trigger. Always at the top.
  - **Bull case** — from senior-analyst.
  - **Bear case** — from devil's-advocate. Collapsible; expanded by default.
  - **What an attacker would say** — from devil's-advocate + forensic. Collapsible; collapsed by default.
  - **Next three questions** — system-anticipation pattern.
  - **Citations** — a list of citation cards (URL + retrieved-at + confidence + inline actions: open in browser, copy URL, view cached snippet).
  - **Gaps** — what the system couldn't answer (abstention).
  - **Tensions** — contradictions between sources (not averaged away).
- A cost footer at the bottom: `Σ $0.00 · 5.2k in · 1.1k out · {wallclock}s`.
- An **Export** button (Phase 5): saves `.md` + `.json` + `.labourious-flow.json` to a user-chosen path.

### 5.3 History section (Phase 5)

- Collapsible. Browses `~/.labourious/theses.db` (the thesis register, shared with the TUI).
- Per-ticker list of prior theses with conviction, date, and a "What changed" diff against the prior version (reusing the TUI's structured-diff logic).
- Click a thesis → loads its graph + inputs into the canvas for re-run.

---

## 6. Ticker input

The ticker (or tickers, for compare graphs) is entered in a field in the top bar or at the top of the right panel. A single ticker is the default; a comma-separated list (e.g. `NVDA, AMD, INTC`) triggers a compare-graph (one branch per ticker, fanned out). The input is part of the saved `.labourious-flow.json` (so a flow is re-runnable with its original ticker, but the ticker is editable on reload).

---

## 7. Empty / error states

| State | What the user sees |
|---|---|
| **First launch (empty canvas)** | A center-canvas hint: "Drag an agent from the left panel to begin. Try: drag senior-analyst, then final-report, then connect them." Plus a "Load a template" link (Phase 5). |
| **Runtime starting** | Top bar: `[○ runtime: starting…]`. Canvas is interactive but Run is disabled. |
| **Runtime disconnected** | Top bar: `[✗ runtime: disconnected]`. Red banner: "Runtime not reachable. Click to retry or open Settings → Runtime." |
| **No API key set** | On Run: red banner (per §4.4 validation). |
| **Connector FAILED mid-run** | The agent node's footer shows `[tool failed: news_8k — SSL blocked]`. The right-panel memo section surfaces the failure in the Gaps card. |
| **All-free mode + paid model selected** | On Run: a confirmation modal: "This run will use {paid model} for {agent}. Estimated cost: ${X}. Continue?" |
| **Graph cycle** | Red banner above canvas (per §4.4). Run disabled. |
| **Partial-failure (one agent failed)** | The failed node shows `✗`; downstream nodes show `–` (skipped). The right panel shows partial envelopes in a "Partial results" card. A "Resume from {failed agent}" button appears (Phase 2+). |

---

## 8. Accessibility / keyboard determinism

Everything must work without a mouse. Tab cycles through: top bar → left panel sections → canvas nodes → right panel sections. All canvas interactions (connect, delete, duplicate) have keyboard equivalents (per §4.3). React Flow's built-in keyboard support covers most; we add the rest.

---

## 9. Theme

A single dark-mode theme, matching the TUI's `Labourious` palette:

- Background: near-black (`#0e1014`).
- Foreground: warm gray (`#d4d4d4`).
- Node accents: orchestrator = teal, senior-analyst = gold, forensic = blue, devils-advocate = red (subtle), final-report = green.
- Edges: subtle gray (`#5d6c7b`); selected edge = brighter.
- Borders: thin (1px), single line.

Light mode is **not** in v1 — same call as the TUI's `style.tcss` (dark-only). Defer to v2.

The layout adapts to window width:

- ≥ 1280px: full three-pane (280 / flex / 420).
- 1024–1279px: narrower side panels (240 / flex / 360).
- < 1024px: side panels collapse to icons; click to expand as overlays. (The app's minimum window size is 1024×768 — smaller windows are not supported in v1.)

---

## 10. What this spec doesn't say

- The graph JSON schema and WS event contract — see [`PROTOCOL.md`](PROTOCOL.md).
- The agent-library catalog contents — see [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md).
- File structure and line budgets — see [`IMPLEMENTATION.md`](IMPLEMENTATION.md).
- The build phases and their acceptance criteria — see [`ROADMAP.md`](ROADMAP.md).
