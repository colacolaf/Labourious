# App Docs — the Labourious Desktop Studio

> The **Labourious Desktop Studio** — a Tauri 2 + React + React Flow desktop app that turns the 5-prompt runtime into an n8n-style agent-flow builder. Local-first. Same runtime as the TUI. Same `~/.labourious/` state. A second **surface**, not a second **product**.

If you read three files, read these in this order:

1. **[`CONTEXT.md`](docs/CONTEXT.md)** — why the app exists and how it relates to the TUI and the existing docs tree.
2. **[`ROADMAP.md`](docs/ROADMAP.md)** — the 5-phase build order with acceptance criteria. This is what to pick up next.
3. **[`SPEC.md`](docs/SPEC.md)** — the three-pane layout, node types, panels, keybindings, and interaction model.

Then the rest, by role:

---

## Framing decisions

| File | Purpose |
|------|---------|
| [`CONTEXT.md`](docs/CONTEXT.md) | Why an app sibling, why now, how it honors `CANNOT-DO.md` and `FRONTEND-DECISION.md` |
| [`STACK-DECISION.md`](docs/STACK-DECISION.md) | Why Tauri 2 + React Flow + bundled Python sidecar (the research that picked each) |
| [`USER-JOBS.md`](docs/USER-JOBS.md) | How the 5 user jobs map to the app surface — the litmus test for any new feature |
| [`CANNOT-DO.md`](docs/CANNOT-DO.md) | The app-specific scope boundaries. Read this against `docs/CANNOT-DO.md` — both win. |

---

## Build plan

| File | Purpose |
|------|---------|
| [`ROADMAP.md`](docs/ROADMAP.md) | The 5-phase build order: canvas → execution → library → forcer → parity. Acceptance per phase. |
| [`IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) | File plan, line budgets, the Python WebSocket bridge spec, what goes where. |

---

## Specs

| File | Purpose |
|------|---------|
| [`SPEC.md`](docs/SPEC.md) | The three-pane layout, agent-node types, left/right panel contents, keybindings, empty/error states. |
| [`PROTOCOL.md`](docs/PROTOCOL.md) | The `.labourious-flow.json` graph schema, the WebSocket event bridge contract, node-type registry. |
| [`AGENT-LIBRARY.md`](docs/AGENT-LIBRARY.md) | The curated catalog of installable agent nodes (technical, quant, macro, flow-and-transcript, research-forcer). |

---

## What the app is (in one paragraph)

The Desktop Studio is a visual orchestration surface for the Labourious runtime. The user drags agent nodes onto a canvas, wires them into a graph, and presses Run. The app compiles the graph into a wave plan, sends it to the local Python runtime over a WebSocket, and streams `AgentStarted` / `AgentFinished` / `ConnectorRequested` events back into a right-side panel that renders the final memo as Markdown. The 5 built-in prompts (`orchestrator` / `senior-analyst` / `forensic-accounting` / `devils-advocate` / `final-report`) are always available; a curated agent library adds focused deep-dive agents (technical, quant, macro, flow-and-transcript) plus a research-forcer directive-injector node that forces any upstream agent to dig deeper. The TUI stays as-is — the app is a second consumer of the same `run_flow_stream()` protocol, not a re-platform.

---

## Quick start (planned)

```
# Once the app ships — download the .dmg / .msi, double-click.
# The app bundles Python + all deps + the runtime as a sidecar.

$ open Labourious.app                    # macOS
$ Labourious.exe                         # Windows

# Power-user override: connect to an existing runtime instead of the bundled one.
$ pip install labourious                  # install the runtime separately
# In Settings → Runtime: set "Connect to existing runtime" → http://127.0.0.1:8765
$ labourious serve --port 8765           # start the WS bridge manually
```

Expected first experience: an empty canvas with the 5 built-in agent nodes in the left-side library panel, ready to drag onto the canvas. Wire them up, press Run, watch the right-side panel stream the f1-equivalent memo for NVDA.

---

## The directory tree

```
app/
├── README.md               ← you are here
├── docs/
│   ├── CONTEXT.md          ← read first
│   ├── STACK-DECISION.md   ← why Tauri + React Flow + bundled Python
│   ├── ROADMAP.md          ← read second
│   ├── USER-JOBS.md        ← the 5 jobs as they apply to the app
│   ├── CANNOT-DO.md        ← app-specific scope boundaries
│   ├── SPEC.md             ← read third
│   ├── PROTOCOL.md         ← graph JSON + WS event bridge contract
│   ├── AGENT-LIBRARY.md    ← the installable agent-node catalog
│   └── IMPLEMENTATION.md   ← file plan + bridge spec
├── src/                    ← React + React Flow frontend (Phase 1+)
│   ├── components/         ← three-pane layout, node types, panels
│   ├── store/              ← graph state, event stream state (Zustand)
│   ├── lib/                ← WS client, mock event generator, graph compiler
│   └── styles/             ← CSS
├── src-tauri/              ← Rust shell + WS config + sidecar launcher (Phase 1+)
├── bridge/                 ← thin Python WS server wrapping run_flow_stream (Phase 2+)
├── agent-library/          ← curated agent-node catalog definitions (Phase 3+)
└── package.json
```

The `src/`, `src-tauri/`, `bridge/`, and `agent-library/` directories are **empty placeholders until their phase ships** — see [`ROADMAP.md`](docs/ROADMAP.md). The docs are the spec; the code follows.

---

## How to use this file

Pick the next phase in [`ROADMAP.md`](docs/ROADMAP.md). Each phase has a goal, a deliverable, acceptance criteria, and the phase it unblocks. Read [`SPEC.md`](docs/SPEC.md) for what to build, [`PROTOCOL.md`](docs/PROTOCOL.md) for the contract the app and runtime share, and [`IMPLEMENTATION.md`](docs/IMPLEMENTATION.md) for where the code goes.
