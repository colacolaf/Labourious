# SPEC — the TUI's components, layout, and behavior

> **Audience:** a developer implementing the TUI. The spec is for the **shape** of the TUI — what the user sees, what they can do, what happens. Implementation details are in [`IMPLEMENTATION.md`](IMPLEMENTATION.md); the runtime side is in [`PROTOCOL.md`](PROTOCOL.md).

**Stack:** Textual v4.x + Rich (already in Textual's dependency closure). Python ≥ 3.11.

## 1. Top-level layout

```
┌────────────────────────────── terminal frame ──────────────────────────────┐
│ ┌─── header ─────────────────────────────────────────────────────────────┐ │
│ │  Labourious · [● connected] · f1 · ollama/llama3.3:70b · /Users/.../Lab │ │
│ └────────────────────────────────────────────────────────────────────────┘ │
│ ┌── sidebar (24 cols) ──┐ ┌── chat (remaining) ──────────────────────────┐ │
│ │ Activity               │ │  (scrolling chat — bubbles + streaming text)│ │
│ │ ───                   │ │                                              │ │
│ │ ① orchestrator  ✓ 0.4s│ │  ─────────────────────────────────────────── │ │
│ │ ② senior-analyst  ●   │ │  ▌12:34:56   user                           ▐  │ │
│ │ ③ forensic       …     │ │   Analyze NVDA at $890                       │ │
│ │ ④ devils-advocate     │ │  ▌12:35:01   orchestrator (active)        ▐  │ │
│ │ ⑤ final-report        │ │   Routing to f1. Reading prior thesis ← ... │ │
│ │ ───                   │ │   ▌12:35:08   senior-analyst (2.1s)        ▐  │ │
│ │ Cost                  │ │   Moat wide; price 22% above base-case. ... │ │
│ │ ┌────────────────────┐ │ │   ▌12:35:14   forensic (3.4s)              ▐  │ │
│ │ │ in: 4.2k  out: 1.1k│ │ │   Note 2(b): revenue-recognition shift ...│ │
│ │ │ est: $0.00         │ │ │   ▌12:35:21   devils-advocate (2.0s)      ▐  │ │
│ │ └────────────────────┘ │ │   Steelmanned bull breaks on three legs ...│ │
│ │ ───                   │ │   ▌12:35:24   final-report (1.5s)          ▐  │ │
│ │ Thesis register        │ │   # Bottom line — HOLD (4/5)               │ │
│ │ ┌────────────────────┐ │ │   **Wide-moat franchise at $890 ...**       │ │
│ │ │ ▾ NVDA              │ │ │   Flip trigger: ≤ $720 OR ...               │ │
│ │ │   v3 (today)   4/5  │ │ │   ## Bull case ...                          │ │
│ │ │   v2 (3d ago)  4/5  │ │ │   ## Bear case ...                          │ │
│ │ │   v1 (10d ago) 3/5  │ │ │   ## What an attacker would say ...        │ │
│ │ └────────────────────┘ │ │   ## Next three questions ...               │ │
│ │ ───                   │ │   ## Citations ...                           │ │
│ │  [Q] Quit  [S] Set   │ │  ─────────────────────────────────────────── │ │
│ │  [/] Search  [R] Reset│ │  > analyze NVDA at $890_                    │ │
│ └───────────────────────┘ └──────────────────────────────────────────────┘ │
│ ┌─── footer (1 line) ─────────────────────────────────────────────────────┐ │
│ │ f1 · STANDARD · paid-for: none · token quota OK · hint: /help             │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────────┘
```

The layout is a 3-row grid (`Header`, `Container`, `Footer`) with the middle row holding (`Sidebar`, `Chat`). All using Textual's CSS-style grid (`Horizontal` and `Vertical` widgets, `grid-*` styles).

## 2. Components (widgets)

Five widgets, each a class in `widgets/`:

### 2.1 `MessageBubble` (`widgets/message_bubble.py`)

The fundamental display unit. One bubble per event from the runtime.

| Property | Value |
|---|---|
| Source | `textual.widgets.Static` subclass |
| Renders | `Markdown` via `textual.widgets.Markdown` (Textual v4 streaming-Markdown feature) |
| Header | `role: agent_id | timing | confidence` (e.g. `senior-analyst · 2.1s · HIGH`) |
| Body | the streaming-then-static markdown |
| Footer | `[1 citation]` chip count → clickable |
| Style | light gray bg for user prompt, slightly darker for agent output, blue accent for orchestrator |

**Behavior:**
- On event `agent_started`: bubble appears with a placeholder body (`▌ waiting for response...`).
- On event `agent_chunk`: incremental markdown is appended (Textual's `Markdown.update()` does the streaming-effect rendering).
- On event `agent_finished`: bubble finalizes (header gets the wallclock + confidence label, footer chip count appears).
- On event `agent_failed`: bubble shows the error message + an actionable retry button.

### 2.2 `ActivityPanel` (`widgets/activity_panel.py`)

The sidebar's top section. One row per agent in the current flow.

| Property | Value |
|---|---|
| Source | `textual.widgets.DataTable` subclass |
| Rows | 5 — orchestrator / senior-analyst / forensic-accounting / devils-advocate / final-report |
| Icon states | `○` queued, `◐` running (with a Spinner widget for animation), `●` done, `✗` failed, `–` skipped |
| Columns | `agent`, `state`, `wallclock`, `tokens` |

**Behavior:**
- Updates reactively on each `agent_started` / `agent_finished` event.
- "Done" rows persist between runs; "queued" rows reset.
- Color: active row tinted; failed row red; skipped row dim.

### 2.3 `CostWidget` (`widgets/cost_widget.py`)

Sub-widget of the sidebar. Cumulative token / cost totals for the current run.

| Property | Value |
|---|---|
| Source | `textual.widgets.Static` |
| Layout | three small lines: `in: {n}k`, `out: {n}k`, `est: ${d}` |
| Updates | per `cost_total` event |

### 2.4 `DiffPanel` (`widgets/diff_widget.py`)

A collapsible card between the agent bubbles and the final memo, **only** if a prior thesis exists for the ticker in the thesis register.

| Property | Value |
|---|---|
| Source | `textual.widgets.Collapsible` |
| Header | "What changed since v(n−1) · {[date]}" |
| Body | side-by-side comparison: prior thesis one-liner vs. new thesis one-liner, prior next-three-questions → new next-three-questions |

### 2.5 `CitationChip` (`widgets/citation_chip.py`)

The footer's citation count `[N citations]` is a clickable chip that opens a modal showing every citation with its URL + a snippet from the retrieved text.

### 2.6 `PromptInput` (`textual.widgets.Input`)

The bottom prompt bar. Multi-line (`textarea=False`, single-line for v1; v2 can be multi-line).

## 3. Keybindings

| Key | Action |
|---|---|
| `Enter` | submit prompt (runs the current flow on the supplied ticker/question) |
| `Ctrl+Enter` | submit prompt with explicit `--depth STANDARD` (default) |
| `Ctrl+L` | clear chat |
| `Ctrl+R` | re-run the last prompt |
| `/` (in input) | open command palette: `/help`, `/flow f1`, `/ticker NVDA`, `/model ollama/...`, `/settings`, `/history`, `/quit` |
| `s` | open Settings modal |
| `h` | open History (thesis register browser) modal |
| `q` / `Ctrl+C` | quit |
| `?` | open help card |

The single-letter commands (`s`, `h`, `q`) are **only** active when the input is not focused, so typing letters in the prompt doesn't trigger shortcuts.

## 4. Modal screens

Two modal screens overlaid via Textual's `ModalScreen`:

### 4.1 `SettingsScreen` (`screens/settings.py`)

Reads/writes `~/.labourious/config.json`. Fields:

| Section | Field | Type |
|---|---|---|
| Providers | provider list (Anthropic, Ollama, Groq, OpenAI, etc.) with per-provider `base_url` + `api_key` reference |
| Default model | `--model` flag default (`ollama/llama3.3:70b`) |
| Per-agent overrides | map of `agent_id → model_name` (e.g. `final-report → anthropic/claude-sonnet-4-5`) |
| Connectors | per-tool provider (sec_edgar keyless, news google_rss or newsapi, market_data yfinance + fred_key, web_fetch no-config) |
| Hybrid routing | checkboxes for each agent whose output should run on the paid model |
| Defaults: `--depth`, `--compressed` | dropdown + checkbox |
| Secrets | button → opens native OS keychain (via `keyring` lib) |

**File schematic:**

```
~/.labourious/
├── config.json          # the canonical state (this is what settings edits)
├── cost.log             # append-only cost log
└── history/             # chat sessions
```

### 4.2 `HistoryScreen` (`screens/history.py`)

Browser for `docs/runtime/thesis_register/theses.db`. Per-ticker list, expandable to view a thesis + its updates + its catalysts.

## 5. Theme

A single dark-mode theme (`Labourious`) defined in `style.tcss`:

- Background: near-black (`#0e1014`).
- Foreground: warm gray (`#d4d4d4`).
- Agent accents: orchestrator = teal, senior-analyst = gold, forensic = blue, devils-advocate = red (subtle, not alarming), final-report = green.
- Borders: thin (single line).
- Source priority indicators: `#5d6c7b` (subtle) for `Tertiary`, brighter for `Primary`.

Theme adapts to terminal width:

- ≥ 120 cols: full sidebar (24 cols) + chat pane.
- 80–119 cols: narrow sidebar (16 cols, just activity), chat pane.
- < 80 cols: sidebar collapses to a single keyboard-toggle button (`Ctrl+B`); full chat pane.

## 6. Empty / error states

| State | What the user sees |
|---|---|
| **First launch** | A welcome card in the chat pane: "Run f1 on a ticker to begin. Try: `analyze NVDA`." |
| **No API key set** | A red banner in the footer: "Missing `ANTHROPIC_API_KEY` — open Settings (s) to set." |
| **Tool unreachable** | A yellow banner with the failing tool's name + retry button. |
| **All-free mode + Sonnet requested** | A warning that the user is being charged; an opt-in confirmation modal. |
| **Connector FAILED** | The corresponding bubble shows `[tool failed: N=retries; fallback to ...]` |

## 7. Accessibility / keyboard-determinism

Everything must work without a mouse. Textual's keyboard-first ethos supports this; we just don't introduce any mouse-only affordances.

## 8. What this spec doesn't say

- Code structure (see [`IMPLEMENTATION.md`](IMPLEMENTATION.md)).
- Event types (see [`PROTOCOL.md`](PROTOCOL.md)).
- The exact phrases of error messages (those are UX polish, decided per-failure during implementation).
