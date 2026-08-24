# STACK-DECISION — why Tauri 2 + React Flow + bundled Python sidecar

> The decision: **Tauri 2 + React 18 + React Flow (xyflow) + a bundled Python sidecar over a local WebSocket.** Not Electron. Not a hosted web app. Not native. Not in-browser. Local-first, desktop-only, with the existing Python runtime untouched.

This file is the research that picked each layer. It is the app's equivalent of `docs/FRONTEND-DECISION.md` — the TUI decision the app revisits. Read [`CONTEXT.md`](CONTEXT.md) for the why-an-app framing; this file is the how.

---

## The constraint set (from prior docs + the user's vision)

| Constraint | Source | Implication |
|------------|--------|-------------|
| Local-first, no Labourious backend | `docs/CANNOT-DO.md` §3 | Hosted web app = strictly out. The "backend" must be a local sidecar. |
| 5 user jobs: trust, action, speed, defensibility, comparison | `docs/USER-JOBS.md` | The canvas must show *evidence* (citations, agent activity, streaming) — not just answers. |
| Runtime is Python, already built | `docs/runtime/runtime.py` | Don't rewrite the runtime. Bridge to it. |
| `run_flow_stream()` is a typed event iterator designed to cross a process boundary | `docs/frontend/PROTOCOL.md` | The WS bridge is a thin wrapper, not a re-implementation. |
| "Not in the browser" (spirit, not letter) | user instruction, carried from TUI decision | Tauri's OS webview satisfies the spirit (no hosted tab); a hosted web app does not. |
| Desktop (macOS + Windows), not mobile | user decision | Rules out React Native's mobile-first tooling as the primary target. |
| Mixed audience: retail + analysts | user decision | Zero-Python-literacy install path required (retail); power-user override available (analysts). |
| n8n-style visual flow builder | user vision | A node-based canvas with drag, connect, fan-out, live status. |
| Agent library: 5 built-ins + focused deep-dive agents + research-forcer injector | user decision | Node types must be extensible without app rebuilds. |
| Sharing: files, no marketplace | `docs/CANNOT-DO.md` + user pick | Graphs export/import as `.labourious-flow.json` files. |
| Strictly local: sync to a paired laptop | user pick | The bundled sidecar runs on the user's machine; no cloud. |

---

## Layer 1: the shell — Tauri 2

### Options considered

| Option | Stack | Pros | Cons | Verdict |
|--------|-------|------|------|---------|
| **A. Tauri 2** | Rust shell + OS webview + JS frontend | ~3–10 MB binary; ~40–80 MB RAM at idle; uses the OS webview (not a hosted tab); mature in 2026; Rust shell is small and auditable; sidecar-process spawning is a first-class feature | Rust build step; some platform-specific webview quirks (WebKit on macOS, WebView2 on Windows) | **Chosen** |
| B. Electron | Chromium + Node + JS frontend | Mature tooling; auto-update; widest reach; one language (JS) end-to-end | ~120–200 MB binary; ~150–400 MB RAM at idle; bundles a full Chromium; contradicts the "lightweight, local-first" spirit | Rejected — bundle size is a real cost for a mixed audience including retail users on metered connections |
| C. Native (SwiftUI + WinUI 3) | Two native codebases | Best performance + platform feel; no webview at all | Two codebases to maintain; steeper build tooling; React Flow (the canvas layer we need) doesn't run natively | Rejected — the canvas requirement forces a webview anyway |
| D. Wails (Go + webview) | Go shell + webview | Lean like Tauri; Go is simpler than Rust | Smaller ecosystem than Tauri in 2026; less mature sidecar tooling | Rejected — Tauri's sidecar + plugin ecosystem is more mature |
| E. Hosted local web app (browser tab) | Vite + React + local server | Easiest to build; hot-reload | Violates the "not in the browser" spirit the TUI decision established | Rejected — same reason as the TUI's 2025 rejection |

### Why Tauri 2 specifically

1. **Bundle size**: 2026 benchmarks (tech-insider.org, rustify.rs, intuz.com) put Tauri's "Hello World" at ~3.2 MB vs Electron's ~85 MB — **96% smaller**. For a mixed audience including retail users, this is the difference between a 30-second download and a 5-minute one.
2. **RAM at idle**: ~40–80 MB vs Electron's ~150–400 MB. The real work happens inside the Python sidecar; the shell should be lean.
3. **Sidecar is first-class**: Tauri's `sidecar` feature bundles a binary and spawns it on app launch — exactly what we need for the Python runtime. No manual subprocess orchestration.
4. **OS webview, not Chromium**: Uses WebKit (macOS) / WebView2 (Windows). Satisfies the "not in the browser" letter (no browser tab) and spirit (no hosted web app).
5. **Mature in 2026**: Tauri 2 shipped stable in 2024; by 2026 it's the default recommendation for new cross-platform desktop apps that don't need Electron's specific advantages.
6. **Rust shell is auditable**: The shell is ~500 lines of Rust; security review is feasible. For an app that handles API keys (even locally), this matters.

### The one real cost

Tauri uses the OS webview, which means **WebKit on macOS, WebView2 on Windows**. These are not bit-identical — there are edge cases in CSS rendering and JS API availability. Mitigation: target the intersection (both support modern ES2022+, CSS Grid, Flexbox, WebSocket); test on both platforms per release.

---

## Layer 2: the frontend — React 18 + React Flow (xyflow)

### Why React (not Svelte, Vue, or Solid)

1. **React Flow is React-only**. The canvas library we need doesn't exist for Svelte or Vue at the same maturity. (Vue Flow exists as a port; it's less mature.)
2. **React 18's concurrent rendering + Suspense** maps cleanly to a streaming-event UI — the right-side panel updates as events arrive without blocking the canvas.
3. **Tauri's official templates default to React** — least friction for the shell + frontend integration.
4. **Ecosystem**: drag-and-drop, Markdown rendering (`react-markdown`), state management (`zustand`) all have battle-tested React libraries. Svelte would mean porting or re-implementing.

### Why React Flow (xyflow) for the canvas

React Flow is the **de-facto standard for n8n-style node editors in 2026**. The research:

- **MIT-licensed, actively maintained** by xyflow (the company behind it).
- **Battle-tested**: the 2026 search results surface Waldiez (agent-orchestration canvas), Workflow Builder (embeddable editor SDK), and dozens of AI-agent canvases — all built on React Flow.
- **Custom node types**: a first-class API for defining node types with arbitrary React components as the node body. We need this for agent nodes (with status indicators, model dropdowns, citation counts).
- **Edge routing**: built-in edge types (bezier, step, smoothstep) + custom edge renderers. We need this for the research-forcer (a special edge that injects a directive) and for visual fan-out.
- **Zoom/pan/selection**: out of the box. No re-implementation.
- **Performance**: handles 100s of nodes smoothly; our graphs will be 5–15 nodes.
- **Live state updates**: nodes can re-render reactively as the runtime streams events — the canvas shows `queued → running → done` in real time.

Alternatives considered: **JointJS** (commercial, heavier), **diagrams.net embed** (not React-native, awkward to integrate), **LiteGraph.js** (older, less React-friendly), **Rete.js** (viable alternative, similar feature set, smaller community). React Flow wins on community + maturity.

### The state layer: Zustand

For graph state (nodes, edges, selection) and event-stream state (the right-panel transcript), **Zustand** over Redux/Context:

- **Minimal boilerplate** — a single `create()` call per store.
- **No provider nesting** — stores are module-level singletons.
- **Selector-based re-rendering** — only the components that read a slice re-render when it changes. Critical for a canvas that must not re-render on every event tick.
- **Works natively with React Flow** — React Flow's own state management is designed to interoperate with external Zustand stores.

---

## Layer 3: the runtime bridge — bundled Python sidecar + WebSocket

### The bridge contract (in one paragraph)

The app launches a bundled Python process on startup (Tauri sidecar). The Python process runs a thin WebSocket server on `127.0.0.1:<port>` that wraps the existing `run_flow_stream()` iterator. The app's React frontend connects to that WS, sends a `run_flow` message with a serialized graph (see [`PROTOCOL.md`](PROTOCOL.md)), and receives a stream of typed events (`FlowStarted`, `AgentStarted`, `AgentFinished`, …) until `FlowFinished` / `FlowFailed`. The Python side is ~200–400 lines of glue; the runtime itself is untouched.

### Why bundled sidecar (not "discover user-installed runtime" only)

The user picked a **mixed retail + analyst audience**. Retail users don't have Python installed and shouldn't need to. The bundled sidecar ships Python + all deps inside the `.app` / `.exe` — double-click, it works. Analysts who already have `pip install labourious` can override in Settings to connect to their existing runtime instead.

### How the Python sidecar is bundled

Two viable paths; the implementing agent should pick based on 2026 tooling maturity at build time:

1. **PyOxidizer / PyOxidizer-style embedding** — embeds the Python interpreter + all deps into a single binary. Smallest footprint, hardest to debug.
2. **Standalone Python distribution + bundled `site-packages`** — ship a portable Python (e.g. python-build-standalone) + a `site-packages` directory with all deps. Larger (~40 MB) but trivially debuggable — you can run the same Python from a terminal.

**Recommendation**: start with option 2 (portable Python + site-packages) for dev velocity; consider PyOxidizer for a leaner v2 binary if bundle size becomes a complaint.

### Why WebSocket (not HTTP SSE, not stdin/stdout, not Tauri's `invoke`)

1. **WebSocket is bidirectional** — the app sends `run_flow` / `cancel_flow` / `update_config` messages; the runtime streams events back. SSE is server→client only, which would require a second HTTP channel for client→server commands.
2. **WebSocket stays open across the whole run** — one connection, N events, no reconnection logic. HTTP would need polling or SSE+POST.
3. **stdin/stdout would require the Python process to be a child of the Tauri shell with piped stdio** — feasible but loses the clean process boundary (a Python crash takes down the shell; with WS, the shell can detect the crash and restart the sidecar).
4. **Tauri's `invoke` (Rust↔JS IPC) doesn't cross to Python** — it's shell-internal only. We still need a transport between the Python sidecar and the React frontend; WS is that transport.

### The bridge protocol in brief

See [`PROTOCOL.md`](PROTOCOL.md) §3 for the full contract. The shape:

```
App (React)                         Bridge (Python, bundled)
    │                                        │
    │── WS connect to 127.0.0.1:<port> ────►│
    │                                        │
    │── { kind: "run_flow",                  │
    │     graph: {...}, inputs: {...} } ───►│  runtime.run_flow_stream(...)
    │                                        │
    │◄─ { kind: "flow_started", ... } ──────│
    │◄─ { kind: "agent_started", ... } ─────│
    │◄─ { kind: "agent_chunk", ... } ───────│  (streamed)
    │◄─ { kind: "connector_requested", ...}│
    │◄─ { kind: "connector_completed", ...}│
    │◄─ { kind: "agent_finished", ... } ───│
    │◄─ { kind: "cost_delta", ... } ────────│
    │   ...                                  │
    │◄─ { kind: "flow_finished", ... } ─────│  (terminal)
    │                                        │
    │── { kind: "cancel_flow" } ──────────►│  (optional, mid-run)
    │◄─ { kind: "flow_cancelled" } ─────────│
```

The bridge is a **stateless translator** between WS JSON and the Python `Event` dataclasses in `docs/runtime/events.py`. It owns no business logic.

---

## Layer 4: the agent-library catalog — JSON, not code

Agent-library nodes (technical, quant, macro, flow-and-transcript, sentiment, research-forcer) are **defined as JSON files** in `app/agent-library/`, not as compiled-in code. Each file declares a node's `id`, `display_name`, `description`, `inputs`, `outputs`, `default_model`, `system_prompt_ref` (a path into `docs/prompts/` or a forked variant), and `connectors_consumed`. The app loads the catalog at startup; users install a node by dragging it from the library panel onto the canvas. **No app rebuild to add a node** — drop a JSON file in the folder, restart, it appears. See [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md).

---

## Cost-of-add vs. cost-of-leave

| Choice | What you give up | What you gain |
|--------|------------------|---------------|
| **Tauri + React Flow now** | A pure-Python UI (would reuse some Textual widget logic). Browser-based distribution. | A real n8n-style canvas that the TUI structurally cannot offer. Ship in weeks once Phase 1 prototype proves out. Reach the mixed audience the TUI can't. |
| Electron instead | Bundle size (~150 MB), RAM (~300 MB idle) | Mature auto-update; one language (JS) end-to-end; wider non-technical-user familiarity |
| Native (SwiftUI + WinUI) | Two codebases; lose React Flow | Best performance; smallest binary; no webview quirks |
| Hosted web app | The "local-first, no backend" principle | Easiest dev; hot-reload; zero install |

The decision is **Tauri 2 + React Flow + bundled Python sidecar** for v1, with the option to revisit if (a) bundle size becomes a real complaint → PyOxidizer, (b) webview quirks dominate → consider native for v2.

---

## What remains open

Three small open questions, to be resolved during Phase 1 prototype:

1. **WebSocket port selection** — pick a free port on startup (Tauri passes it to the sidecar as a CLI arg) vs. fixed port `8765`. Recommendation: **pick a free port** — avoids "port in use" failures on machines with other local servers.
2. **Sidecar lifecycle** — does the app keep the sidecar running across app restarts (background daemon) or spawn-per-session? Recommendation: **spawn-per-session** — simpler, no orphan processes, matches "double-click and it works."
3. **Auto-update** — Tauri has an auto-updater plugin; should we enable it for v1? Recommendation: **no for v1** — the app is local-first and the runtime+prompts are shared with the TUI, so updates should be coordinated across both surfaces. Defer to v2.

These three are small. They go to [`IMPLEMENTATION.md`](IMPLEMENTATION.md), not back here.
