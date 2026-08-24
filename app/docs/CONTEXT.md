# CONTEXT — why the app exists

> Read this first. Why a desktop app sibling exists alongside a working TUI, and how the two surfaces share a runtime without drifting.

## TL;DR

The Labourious TUI shipped. It's stable (3,000+ green smoke assertions, 17/17 evals, 46 pilots, all 10 flows wired). It also has an adoption ceiling: it caps at power users who live in terminals. The Desktop Studio is the v2 surface the docs always anticipated — `docs/FRONTEND-DECISION.md` explicitly names "a Tauri/local-web-app migration as a v2+ option **if shipped adoption justifies it**." The adoption ceiling is what justifies it.

The app is **not a re-skin of the TUI**. It is an n8n-style agent-flow builder: the user drags agent nodes onto a canvas, wires them into a graph, and the runtime executes the graph. The TUI consumes a *fixed* flow (`execute_flow_f1` … `f10`); the app lets the user *build* the flow. That's a flow-compiler layer the TUI structurally cannot offer, and it's where the pluggable-agents idea that `docs/DEFERRED.md` and `docs/ROADMAP.md` P2 item 14 parked finally earns a home.

This file is the short tour. The build sequence is in [`ROADMAP.md`](ROADMAP.md). The visual + interaction spec is in [`SPEC.md`](SPEC.md). The contract between the app and the runtime is in [`PROTOCOL.md`](PROTOCOL.md).

---

## What the Desktop Studio is, in one paragraph

A Tauri 2 desktop app (macOS + Windows) that wraps a React + React Flow frontend. The user interacts with a three-pane layout: a left panel of settings + agent-library (drag-source), a center canvas of agent nodes + edges (the workspace), a right panel that streams runtime events and renders the final memo as Markdown. The app talks to the Python runtime over a local WebSocket — no Labourious backend, no accounts, strictly local-first. The runtime is the same `docs/runtime/runtime.py` the TUI uses; the app is a second consumer of the same `run_flow_stream()` event protocol. The 5 built-in prompts are always-on nodes; a curated agent library adds focused deep-dive agents (technical, quant, macro, flow-and-transcript) plus a research-forcer directive-injector that forces any upstream agent to dig deeper.

---

## Why an app, why now

Three forces converge:

### 1. The TUI hit its adoption ceiling

The TUI is a terminal tool. It reaches power users who live in terminals — the audience `docs/USER-JOBS.md` named for v1 (Wharton teams, junior analysts). It does not reach the other half of the v1 audience: **retail investors evaluating before talking to their advisor**. Retail investors do not live in terminals; they live on phones and desktops. `docs/USER-JOBS.md` explicitly flags this as pressure-testable: *"if real adoption is retail, 'comparison is job 5' rank might be too low."* The audience question is what drove the decision.

### 2. The runtime was always built to be consumed twice

`docs/frontend/PROTOCOL.md` defined the runtime's contract as a typed event iterator (`FlowStarted`, `AgentStarted`, `AgentFinished`, `ConnectorRequested`, `ThesisWritten`, `CostDelta`, …) with an explicit forward-compatibility clause: *"the same iterator interface becomes a JSON-over-stdout / IPC boundary if we ever split the runtime into a separate process."* This is that split. The runtime stays untouched; the app wraps `run_flow_stream()` in a WebSocket bridge and consumes the same events the TUI does. **No runtime rewrite; the app is a second consumer of the same protocol.**

### 3. The 2026 market gap is real

A 2026 search for "mobile investment research app citation grounded LLM" surfaces AlphaSense, Barebone AI, V7 Labs, ThesisLoop — all shipping polished apps. None is citation-grounded + abstention-honest + free-model-friendly in the way Labourious is. The differentiator (Job 1 — Trust) is *harder* to deliver on a desktop surface than on a TUI, which is exactly why it's the strongest defensible position.

### 4. The pluggable-agents idea finally has a home

`docs/DEFERRED.md` and `docs/ROADMAP.md` P2 item 14 both parked "pluggable agents" with the gate *"Re-hire if: a Wharton team or sector user demands sector-specific framing."* The app's agent-library catalog is that gate opening — a curated set of focused deep-dive agents (technical, quant, macro, flow-and-transcript) that users drag onto the canvas as nodes. **The app is where the deferred pluggable-agents policy earns its keep.**

---

## How the app relates to the TUI

| Axis | TUI (`docs/frontend/`) | App (`app/`) |
|------|------------------------|--------------|
| **Surface** | Terminal (Textual v4 + Rich) | Desktop (Tauri 2 + React + React Flow) |
| **Flow model** | Fixed — user picks from f1–f10 | User-built — drag nodes, wire edges, compile to a custom wave plan |
| **Runtime** | In-process (one Python process, iterator) | WebSocket to a bundled Python sidecar (separate process) |
| **State** | `~/.labourious/config.json`, `theses.db`, `.runs/` | Same — shares `~/.labourious/` and `theses.db` with the TUI |
| **Audience** | Power users (analysts, Wharton teams) | Mixed (retail + analysts) |
| **Agent roster** | The 5 built-in prompts | 5 built-in + curated agent-library (technical, quant, macro, flow-and-transcript, research-forcer) |
| **Parallelism** | Implicit in flow recipes (e.g. f1 wave-3) | Explicit — user wires fan-out branches; runtime runs them via `ThreadPoolExecutor` |
| **Status** | Shipped, stable (3,000+ assertions green) | Docs-only (this tree); Phase 1 prototype next |

**Three guarantees the shared-repo structure enforces:**

1. **One protocol** — `docs/runtime/events.py` owns the event types; both `docs/frontend/` (TUI) and `app/` (studio) consume it. The protocol can't drift because there's only one file.
2. **One prompt library** — `docs/prompts/` is shared. The app's agent-library catalog lives in `app/agent-library/` as user-visible node definitions, *not* as a separate prompts tree.
3. **One runtime** — `app/bridge/` is a thin WebSocket wrapper around `run_flow_stream()`. No runtime code duplication.

The TUI stays as-is. It's a real, working v1 surface. The app is the v2 surface that builds on the same foundation — not a replacement.

---

## What changed vs. the TUI's framing

The TUI's `docs/FRONTEND-DECISION.md` explicitly rejected the browser for v1: *"local-first, no backend, runtime is Python so TUI eliminates the IPC bridge."* That reasoning was right *for v1*. The app revisits each constraint:

| TUI constraint (2025) | App revisit (2026) | Why the revisit holds |
|------------------------|---------------------|------------------------|
| Local-first, no backend | Still local-first; the "backend" is a bundled Python sidecar on `127.0.0.1`, not a Labourious server | Honors `docs/CANNOT-DO.md` §3 literally — "No Labourious backend, period." |
| Runtime is Python → TUI eliminates IPC | App accepts the IPC bridge because the value (visual flow-building) exceeds the cost | The WebSocket bridge is ~200 lines of Python; the canvas unlocks an entire new use-case the TUI can't serve |
| Not in the browser | Still not in the browser — Tauri 2 uses the OS webview, not a hosted tab | Satisfies the letter (no browser tab) and the spirit (no hosted web app) of the original constraint |
| Mobile-first UI is a no-build | Desktop app, not mobile — the app serves the laptop audience the TUI already serves, plus a richer visual surface | The no-build line was about *UI priority*, not about the existence of an app sibling |
| "Tauri/local-web-app migration as a v2+ option if shipped adoption justifies it" | Adoption ceiling reached — this *is* that v2 option | The decision was conditional, not permanent; the condition is met |

The app **does not supersede** `docs/FRONTEND-DECISION.md`. It is the v2 the doc anticipated. The TUI decision stands for v1; the app decision stands for v2. Both are valid for their phase.

---

## What is *not* in this app

Explicit non-goals, in one line each:

- **No Labourious-hosted backend.** The runtime runs on the user's machine (bundled sidecar). No accounts, no sync relay, no server-side state. See [`CANNOT-DO.md`](CANNOT-DO.md) §1.
- **No mobile app.** Desktop only (macOS + Windows) for v1. Mobile is a v3+ conversation if the desktop app justifies it. See [`CANNOT-DO.md`](CANNOT-DO.md) §2.
- **No multi-user.** Single-user. The thesis register stays per-user local SQLite. See `docs/CANNOT-DO.md` §7.
- **No broker integration.** Same boundary as the TUI — the app provides analysis, not execution. See `docs/CANNOT-DO.md` §8.
- **No re-implementation of the runtime.** The runtime stays in `docs/runtime/`. The app is a consumer.
- **No fork of the prompts.** The 5 built-in prompts stay in `docs/prompts/`. Agent-library variants live in `app/agent-library/` and reference the shared protocol, not duplicate prompts.
- **No replacement of the TUI.** The TUI is the v1 surface and stays maintained. The app is the v2 surface.

---

## How to read the rest of this docs tree

1. [`STACK-DECISION.md`](STACK-DECISION.md) — why Tauri 2 + React Flow + bundled Python sidecar. The research that picked each.
2. [`ROADMAP.md`](ROADMAP.md) — the 5-phase build order: canvas → execution → library → forcer → parity. What to pick up next.
3. [`SPEC.md`](SPEC.md) — the three-pane layout, node types, panels, keybindings, empty/error states.
4. [`PROTOCOL.md`](PROTOCOL.md) — the `.labourious-flow.json` graph schema, the WebSocket event bridge contract, the node-type registry.
5. [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md) — the curated catalog of installable agent nodes.
6. [`IMPLEMENTATION.md`](IMPLEMENTATION.md) — file plan, line budgets, the bridge spec.
7. [`USER-JOBS.md`](USER-JOBS.md) — how the 5 user jobs map to the app surface (the litmus test).
8. [`CANNOT-DO.md`](CANNOT-DO.md) — the app-specific scope boundaries (read against `docs/CANNOT-DO.md`).

The docs are the spec. The code follows — `src/`, `src-tauri/`, `bridge/`, and `agent-library/` are empty placeholders until their phase ships.
