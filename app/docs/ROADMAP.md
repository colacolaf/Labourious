# ROADMAP — the 5-phase build order

> Roadmap, not backlog. These 5 phases are **ordered by what unblocks what**. Skip a phase and the next one is unprovable.

The order is locked: **canvas → execution → library → forcer → parity.** Each phase has a goal, a deliverable, acceptance criteria, and the phase it unblocks. The phases are sequenced so that the riskiest unknowns (does the canvas+WS bridge work?) are proven before the costliest work (real graph compilation) begins.

---

## The constraint that shapes the order

The app's whole value is a *second consumer* of the existing runtime. Three failure modes guard the build:

1. **Premature execution** — wiring the canvas to the real runtime before the visual + WS bridge layer is proven. If the canvas is wrong, the execution work is wasted.
2. **Premature library** — adding agent-library nodes before custom-graph execution works. The library is meaningless if custom graphs don't run.
3. **Premature parity** — chasing feature-parity with the TUI before the app's distinct value (the canvas) is proven. The app earns its existence by *not* being a TUI clone.

The order below makes these failures impossible to miss, in that order.

---

## Phase 1 — Canvas + mock event stream

**Goal:** A working three-pane shell with a React Flow canvas where the 5 built-in agent nodes are draggable, connectable, and render live status against a **mock** event stream. No real execution.

**Deliverable:** `app/` runs. `npm run tauri dev` launches the desktop app. The user can:
- Drag any of the 5 built-in agents from the left library panel onto the canvas.
- Connect nodes with edges (including fan-out — two edges from one node).
- Press "Run" — the canvas animates nodes through `queued → running → done` states, and the right panel streams a **mock** event sequence that mimics `flow_started → agent_started → agent_chunk → agent_finished → flow_finished`.
- Save/load a graph as `.labourious-flow.json` to/from `~/.labourious/flows/`.

**Acceptance:**
- Three-pane layout renders on macOS and Windows at ≥ 1024×768.
- All 5 built-in agent nodes appear in the left library panel and drag onto the canvas.
- Edges can be created by dragging from a node's output handle to another node's input handle.
- Edges can be deleted (select + Delete).
- Fan-out is expressible: one node → two downstream nodes.
- The "Run" button against the mock stream animates all 5 nodes through their states in order, with per-node wallclock + token counts in the right panel.
- A saved `.labourious-flow.json` round-trips: save → reload → same graph.
- `~/.labourious/flows/` is created on first save if missing.

**What's NOT in Phase 1:**
- Real execution — the runtime is not called. The mock stream is a hardcoded sequence.
- Agent-library nodes — only the 5 built-ins.
- Settings panel content — the left panel has placeholders; provider keys are not yet wired.
- History panel — the right panel shows the current run only.

**Unblocks:** Phase 2. Without a proven canvas, real execution work is built on sand.

**Estimated effort:** 2–3 weeks. The bulk is React Flow node-type definitions + the three-pane layout + the mock event generator. The WS bridge is stubbed (mock stream runs in the React layer; no Python sidecar yet).

---

## Phase 2 — Real execution + WebSocket bridge

**Goal:** The canvas drives the real Python runtime. A graph the user builds compiles into a wave plan, the bridge sends it to `run_flow_stream()` (or a new `run_custom_flow_stream(graph)` entry point), and real events stream back into the right panel.

**Deliverable:**
- A bundled Python sidecar launches on app startup (Tauri sidecar).
- A WebSocket bridge (`app/bridge/server.py`, ~200–400 lines) wraps `run_flow_stream()` and translates Python `Event` dataclasses to JSON WS messages per [`PROTOCOL.md`](PROTOCOL.md) §3.
- A graph compiler (`app/src/lib/graph-compiler.ts`, ~300 lines) takes a React Flow graph (nodes + edges) and produces a wave plan: ordered list of `(agent_id, model, brief, depends_on)` tuples that the runtime can execute.
- The runtime gains a new entry point `run_custom_flow_stream(graph, inputs, default_model)` alongside `execute_flow_f1` … `f10`. **This is the only runtime change** — additive, non-breaking, the 10 built-in flows still work.
- Press "Run" with the 5 built-in agents wired as f1's wave plan → real NVDA memo streams into the right panel with citations, cost totals, and per-agent wallclock.
- Fan-out branches the user wires run in parallel via the runtime's existing `ThreadPoolExecutor(max_workers=2)`.

**Acceptance:**
- A graph matching f1's wave plan (orchestrator → senior-analyst → [forensic, devil's-advocate] in parallel → final-report) produces a valid memo on NVDA with ≥ 80% cited claims (the same bar as the TUI's f1).
- The right panel renders `AgentStarted` / `AgentChunk` / `AgentFinished` / `ConnectorRequested` / `ConnectorCompleted` / `CostDelta` / `FlowFinished` events in real time, with the final memo as Markdown.
- A fan-out branch (two agents downstream of one node) runs concurrently — both `AgentStarted` events fire before either `AgentFinished`.
- A graph with a cycle is rejected at compile time with a clear error message in the right panel.
- A missing API key surfaces as a red banner in the right panel (same shape as the TUI's empty/error states).
- The bridge restarts the sidecar if the Python process crashes mid-run; the right panel shows "runtime restarted — re-run to retry."
- Cost totals in the right panel match the runtime's `logs/cost.json` for the same run.

**What's NOT in Phase 2:**
- Agent-library nodes — still only the 5 built-ins.
- Research-forcer injector — edges are plain pass-through.
- Settings panel content — provider keys come from `~/.labourious/config.json` (shared with the TUI); the app reads but doesn't yet edit.
- History panel — still current-run only.

**Unblocks:** Phase 3. Custom-graph execution proven means the agent-library has a runtime to plug into.

**Estimated effort:** 3–4 weeks. The graph compiler + the runtime's `run_custom_flow_stream` entry point + the WS bridge are the real work.

---

## Phase 3 — Agent library + per-node model routing

**Goal:** The curated agent-library catalog is populated and installable as canvas nodes. Per-node model routing (global default + per-node override) works.

**Deliverable:**
- `app/agent-library/` contains JSON definitions for the 5 catalog agents (see [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md)):
  - **Technical** — price-action/momentum deep-dive, consumes `market_data`.
  - **Quant** — LLM coach over the DCF/Comps/Comparator trio.
  - **Macro** — rates/regime/sector-beta, consumes FRED + `market_data`.
  - **Flow-and-transcript** — insider flow + earnings-call deep-dive in one agent.
  - **Research-forcer** — a directive-injector *edge* node (covered in Phase 4, but its JSON lands here).
- Each library agent has a `system_prompt_ref` pointing to a prompt file under `docs/prompts/library/<agent>/system-prompt.md` (new prompts, written this phase).
- Left panel has an "Agent Library" section below the 5 built-ins; dragging a library agent onto the canvas adds it as a node.
- Each agent node (built-in or library) has a model dropdown in its body: `[default] | ollama/llama3.3:70b | anthropic/claude-sonnet-4-5 | groq/llama-3.3-70b-versatile | …`. Selecting a model sets that node's override.
- The graph compiler reads per-node model overrides and passes them to `run_custom_flow_stream` as `per_agent_model` (the existing runtime precedence rule: per-node > global default).
- A user-built graph with, e.g., senior-analyst on `ollama/llama3.3:70b` + final-report on `anthropic/claude-sonnet-4-5` runs correctly — the final-report agent's `AgentStarted` event carries `model: "anthropic/claude-sonnet-4-5"`.

**Acceptance:**
- All 5 library agents appear in the left panel and drag onto the canvas.
- Each library agent runs end-to-end when wired into a graph with a real ticker (NVDA), producing its expected envelope shape per its `system_prompt_ref`.
- Per-node model dropdown overrides the global default; the `AgentStarted` event's `model` field reflects the override.
- The global default model (set in the left panel) applies to any node without an explicit override.
- A graph that mixes built-in + library agents (e.g. senior-analyst → technical → final-report) runs end-to-end and the right panel streams all agents.
- New prompt files under `docs/prompts/library/` conform to `docs/prompts/V2-PROMPT-STANDARD.md` (the shared envelope schema).

**What's NOT in Phase 3:**
- Research-forcer injector (Phase 4) — the forcer's JSON is in the library but its edge-injection behavior isn't wired.
- Settings panel full content — model dropdowns work; provider key editing is still via the TUI or config.json.
- History panel.

**Unblocks:** Phase 4. The library is the substrate the research-forcer plugs into.

**Estimated effort:** 2–3 weeks. The bulk is writing the 4 new prompts (technical, quant, macro, flow-and-transcript) + the JSON catalog + the per-node dropdown UI.

---

## Phase 4 — Research-forcer directive injector + parallelism

**Goal:** The research-forcer node works as a directive-injector edge between an upstream and downstream agent. Parallelism on fan-out branches is fully wired and visible.

**Deliverable:**
- The **research-forcer** is a special node type, not an agent. When placed between an upstream agent A and a downstream agent B, on Run:
  1. Agent A runs normally and emits its envelope.
  2. The forcer inspects A's envelope, generates a "dig deeper" directive (a structured instruction: "find N more primary sources for sub-claim X", "expand section Y with Z more depth"), and re-runs A with the directive appended to its brief.
  3. A's second-pass envelope is what flows to B.
- The forcer has a configurable `depth_budget` (default 1 extra pass; max 3) and a `directive_template` (editable in the node body).
- The forcer's behavior is **runtime-side** — the graph compiler emits a `directive_inject` step between A's first and second pass; the runtime executes it.
- Parallelism: fan-out branches the user wires run concurrently via `ThreadPoolExecutor`; the canvas visually indicates parallel branches (both nodes show `running` simultaneously; the right panel interleaves their events).
- The runtime's existing `ThreadPoolExecutor(max_workers=2)` is reused; the graph compiler just declares which branches are parallel.

**Acceptance:**
- A graph `senior-analyst → [forcer] → final-report` produces a final-report that cites ≥ 2× the primary sources of the same graph without the forcer (on the same ticker + model).
- The forcer's `depth_budget` caps extra passes — setting it to 0 makes the forcer a pass-through (no second pass).
- The forcer's `directive_template` is editable; changes take effect on the next Run.
- A graph with two parallel branches (e.g. forensic + devil's-advocate both downstream of senior-analyst) shows both nodes in `running` state simultaneously; their `AgentStarted` events arrive before either `AgentFinished`.
- The right panel interleaves events from parallel agents correctly (no event loss, no ordering violation within a single agent).
- The cost footer reflects the forcer's extra passes (≈ 2× the upstream agent's token cost when `depth_budget=1`).

**What's NOT in Phase 4:**
- Settings panel full content.
- History panel.
- Export.

**Unblocks:** Phase 5. The app's distinct value (visual flow-building + the research-forcer) is now proven; what remains is parity with the TUI's surfaces.

**Estimated effort:** 2–3 weeks. The forcer is novel — no existing runtime support; the directive-injection protocol + the second-pass machinery are new runtime code.

---

## Phase 5 — Parity: Settings + History + export

**Goal:** The app reaches parity with the TUI's three core surfaces (Settings, History, export), in app-native form.

**Deliverable:**
- **Left panel: Settings** — full provider key editor (add/edit/delete providers, test connection with the ↻ probe from `docs/runtime/providers.py`), default model, depth toggle, connectors config. Reads/writes `~/.labourious/config.json` + OS keychain — same source of truth the TUI uses.
- **Right panel: History** — a collapsible History section that browses the thesis register (`theses.db`), shows per-ticker prior theses with inline diffs (reusing the TUI's structured-diff logic), and supports re-running a prior flow.
- **Export** — a "Export" button in the right panel that saves the final memo as `.md` + the envelope as `.json` + the graph as `.labourious-flow.json` to a user-chosen path. Mirrors the TUI's `--export` CLI flag.
- **Flow templates** — a small set of read-only curated graph templates (e.g. "f1 equivalent", "semiconductor deep-dive", "earnings review") installable from the left panel as starting points.

**Acceptance:**
- A user can add a provider key in the app's Settings, and the TUI (relaunched) sees the same key — one source of truth.
- The ↻ test button on each provider row reports OK/FAIL/AUTH_MISSING/TIMEOUT/UNREACHABLE + latency (same as the TUI).
- The History panel lists prior theses from `theses.db` with conviction, date, and a "What changed" diff against the prior version.
- Re-running a prior thesis from the History panel loads its graph + inputs into the canvas and runs it.
- Export produces three files (`.md`, `.json`, `.labourious-flow.json`) with content matching the TUI's `--export` output for the same run.
- At least 3 curated templates ship (f1-equivalent, sector deep-dive, earnings review).

**Unblocks:** Ship. After Phase 5, the app is a real v1.

**Estimated effort:** 2–3 weeks. Reusing the TUI's structured-diff + provider-probe logic keeps this lean; the work is the UI.

---

## What isn't on this roadmap (and why)

- **Mobile app.** Out of scope for app v1. Desktop only. Mobile is a v3+ conversation if the desktop app justifies it. See [`CANNOT-DO.md`](CANNOT-DO.md) §2.
- **Cloud sync of graphs/theses.** Out of scope. Strictly local. See [`CANNOT-DO.md`](CANNOT-DO.md) §1.
- **A Labourious-hosted agent marketplace.** Out of scope. Sharing is file-based (`.labourious-flow.json`). See [`CANNOT-DO.md`](CANNOT-DO.md) §3.
- **Multi-user.** Same as the TUI — single-user. See `docs/CANNOT-DO.md` §7.
- **Replacing the TUI.** The TUI stays maintained. The app is a sibling, not a successor.
- **A chart library.** Same as the TUI — memos > dashboards. Markdown tables are sufficient. See `docs/USER-JOBS.md` no-build list.
- **Full TUI slash-command parity.** The app uses a canvas, not a chat input. Slash commands (`/flow`, `/ticker`, `/model`, `/depth`) are replaced by direct canvas manipulation — no need to port them.
- **Real-time market data.** Same as the TUI — delayed OHLCV is enough. See `docs/CANNOT-DO.md` §1.

---

## How to use this file

Pick the next phase on this list. Each phase has a goal, a deliverable, acceptance criteria, and the phase it unblocks. Build phases in order; do not skip. The phase you're on is the only one that matters until its acceptance criteria pass.
