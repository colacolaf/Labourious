# IMPLEMENTATION — file plan, line budgets, bridge spec

> **Audience:** the developer writing the code. This file says where each piece goes, roughly how big it is, and what the WebSocket bridge's Python side looks like. The shape of the app is in [`SPEC.md`](SPEC.md); the contracts are in [`PROTOCOL.md`](PROTOCOL.md); the build order is in [`ROADMAP.md`](ROADMAP.md).

This file maps phases to files. Files listed under a phase are created in that phase; earlier phases don't have them. **Nothing is scaffolded ahead of its phase** — that's how scope-creep happens.

---

## 1. The full file tree (target state, after Phase 5)

```
app/
├── README.md                         (done — this docs tree's index)
├── docs/                              (done — 10 files)
├── package.json                       (Phase 1)
├── tsconfig.json                      (Phase 1)
├── vite.config.ts                     (Phase 1)
├── src-tauri/                         (Phase 1)
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   └── src/main.rs                    (~150 lines — shell + sidecar spawn)
├── src/                               (Phase 1+)
│   ├── main.tsx                       (~20 lines — React root)
│   ├── App.tsx                        (~150 lines — three-pane layout)
│   ├── components/
│   │   ├── TopBar.tsx                 (~80 lines — status + Run button)
│   │   ├── LeftPanel.tsx              (~200 lines — Settings + Library + My Flows)
│   │   ├── Canvas.tsx                 (~250 lines — React Flow wrapper)
│   │   ├── RightPanel.tsx             (~200 lines — activity + memo + history)
│   │   ├── nodes/
│   │   │   ├── AgentNode.tsx          (~120 lines — the agent node body)
│   │   │   ├── ForcerNode.tsx         (~80 lines — research-forcer badge, Phase 4)
│   │   │   └── node-types.ts          (~40 lines — React Flow node-types registry)
│   │   ├── edges/
│   │   │   ├── PassthroughEdge.tsx     (~30 lines)
│   │   │   └── ForcerEdge.tsx          (~60 lines — diamond badge, Phase 4)
│   │   ├── panels/
│   │   │   ├── SettingsSection.tsx    (~150 lines — providers, model, depth, Phase 5)
│   │   │   ├── LibrarySection.tsx    (~100 lines — built-ins + library cards)
│   │   │   ├── MyFlowsSection.tsx     (~120 lines — saved flows list, Phase 1+)
│   │   │   ├── ActivitySection.tsx    (~100 lines — per-agent rows)
│   │   │   ├── MemoSection.tsx        (~180 lines — Markdown render + citation cards)
│   │   │   └── HistorySection.tsx     (~150 lines — thesis register browse, Phase 5)
│   │   └── modals/
│   │       ├── ConnectorsModal.tsx     (~80 lines, Phase 5)
│   │       └── DiagnosticsModal.tsx   (~60 lines)
│   ├── store/
│   │   ├── graph-store.ts             (~150 lines — Zustand: nodes, edges, selection)
│   │   ├── run-store.ts               (~180 lines — Zustand: current run events + memo)
│   │   ├── config-store.ts            (~120 lines — Zustand: config + provider keys, Phase 5)
│   │   └── library-store.ts           (~80 lines — Zustand: agent-library catalog)
│   ├── lib/
│   │   ├── ws-client.ts               (~200 lines — WebSocket client + reconnect)
│   │   ├── mock-events.ts             (~150 lines — Phase 1 mock event generator)
│   │   ├── graph-compiler.ts          (~300 lines — Phase 2: graph → wave plan)
│   │   ├── graph-io.ts                (~120 lines — save/load .labourious-flow.json)
│   │   ├── graph-validate.ts          (~150 lines — cycle/terminal/key validation)
│   │   └── theme.ts                   (~60 lines — colors, node accents)
│   └── styles/
│       └── app.css                    (~200 lines — layout grid, node styling)
├── bridge/                            (Phase 2+)
│   ├── server.py                      (~250 lines — WebSocket server + Event → JSON)
│   ├── compiler.py                    (~300 lines — graph JSON → wave plan)
│   ├── sidecar.py                     (~80 lines — entry point, port selection)
│   └── requirements.txt               (websockets, imports docs.runtime)
└── agent-library/                     (Phase 3+)
    ├── technical.json
    ├── quant.json
    ├── macro.json
    ├── flow-and-transcript.json
    └── research-forcer.json
```

**Total estimated lines (all phases):** ~3,500 lines of TypeScript + ~600 lines of Python + ~200 lines of CSS + ~150 lines of Rust = **~4,450 lines** across 5 phases. That's the same order of magnitude as the TUI's `docs/frontend/` (~3,000 lines of Python + CSS).

---

## 2. Phase-by-phase file plan

### Phase 1 — Canvas + mock event stream

Created files:
- `app/package.json`, `tsconfig.json`, `vite.config.ts` — Vite + React + TypeScript scaffold.
- `app/src-tauri/` — Tauri 2 Rust shell (sidecar not yet wired; mock stream is in-process).
- `app/src/main.tsx`, `App.tsx` — React root + three-pane layout.
- `app/src/components/TopBar.tsx`, `LeftPanel.tsx`, `Canvas.tsx`, `RightPanel.tsx`.
- `app/src/components/nodes/AgentNode.tsx`, `node-types.ts`.
- `app/src/components/edges/PassthroughEdge.tsx`.
- `app/src/components/panels/LibrarySection.tsx`, `MyFlowsSection.tsx`, `ActivitySection.tsx`, `MemoSection.tsx`.
- `app/src/store/graph-store.ts`, `run-store.ts`, `library-store.ts`.
- `app/src/lib/ws-client.ts` (stubbed — no real server yet), `mock-events.ts`, `graph-io.ts`, `graph-validate.ts`, `theme.ts`.
- `app/src/styles/app.css`.

**Not created:** `bridge/`, `agent-library/`, Settings/History panels, `graph-compiler.ts`, `ForcerNode`/`ForcerEdge`.

### Phase 2 — Real execution + WebSocket bridge

Created files:
- `app/bridge/server.py` — WebSocket server wrapping `run_flow_stream` + the new `run_custom_flow_stream`.
- `app/bridge/compiler.py` — graph JSON → wave plan.
- `app/bridge/sidecar.py` — entry point.
- `app/bridge/requirements.txt`.
- `app/src-tauri/src/main.rs` updated to spawn the Python sidecar.
- `app/src/lib/ws-client.ts` — real implementation (replaces the stub).
- `app/src/lib/graph-compiler.ts` — client-side pre-validation + serialization.
- `docs/runtime/runtime.py` — gains `run_custom_flow_stream()` (the only runtime change; additive).

### Phase 3 — Agent library + per-node model routing

Created files:
- `app/agent-library/technical.json`, `quant.json`, `macro.json`, `flow-and-transcript.json`, `research-forcer.json` (the forcer's JSON lands here even though its behavior is Phase 4).
- `docs/prompts/library/technical/system-prompt.md`, `quant/`, `macro/`, `flow-and-transcript/` — the 4 new prompts.
- `app/src/components/nodes/AgentNode.tsx` updated to render the model dropdown.
- `app/src/components/panels/LibrarySection.tsx` updated to load from `agent-library/`.

### Phase 4 — Research-forcer + parallelism

Created files:
- `app/src/components/nodes/ForcerNode.tsx` — the diamond badge node.
- `app/src/components/edges/ForcerEdge.tsx` — the special edge type.
- `app/bridge/compiler.py` updated to emit `directive_inject` steps for forcer edges.
- `docs/runtime/events.py` — gains `DirectiveInjected` + `ForcerPassComplete` events (additive).
- `docs/runtime/runtime.py` — `run_custom_flow_stream` updated to execute forcer passes.

### Phase 5 — Parity: Settings + History + export

Created files:
- `app/src/components/panels/SettingsSection.tsx`, `HistorySection.tsx`.
- `app/src/components/modals/ConnectorsModal.tsx`, `DiagnosticsModal.tsx`.
- `app/src/store/config-store.ts`.
- `app/src/components/panels/MemoSection.tsx` updated with export button.
- Curated flow templates in `app/agent-library/templates/` (3+ `.labourious-flow.json` files).

---

## 3. The WebSocket bridge — Python side

The bridge is the thin Python layer that translates between the app's WS JSON and the runtime's `Event` dataclasses. It owns **no business logic** — it's a stateless translator. Lives in `app/bridge/`.

### 3.1 `app/bridge/sidecar.py` — entry point (~80 lines)

```python
"""Labourious desktop app sidecar — WebSocket bridge to the runtime.

Spawned by the Tauri shell on app startup. Binds a WebSocket server on
127.0.0.1:<auto-port>, prints the port to stdout (the shell reads it and
passes it to the React frontend via Tauri's sidecar API).
"""
import sys
from .server import run_server

def main():
    port = run_server()  # picks a free port, prints it, blocks
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3.2 `app/bridge/server.py` — WebSocket server (~250 lines)

The server handles one WS connection (the app) per session. It dispatches incoming `kind` values to handlers; each handler calls the runtime and streams events back as JSON.

Pseudocode (the real file is ~250 lines):

```python
import json, asyncio, websockets
from docs.runtime import events, runtime

async def handle_connection(ws):
    # hello handshake
    msg = await ws.recv()
    assert json.loads(msg)["kind"] == "hello"
    await ws.send(json.dumps({
        "kind": "hello_ack",
        "runtime_version": "0.1.0",
        "protocol_version": 1,
        "providers_available": list(runtime.list_providers()),
    }))

    async for msg in ws:
        req = json.loads(msg)
        kind = req["kind"]
        if kind == "run_flow":
            await handle_run_flow(ws, req)
        elif kind == "cancel_flow":
            await handle_cancel_flow(ws, req)
        elif kind == "read_config":
            await ws.send(json.dumps({"kind": "config", "config": runtime.load_config().to_dict()}))
        elif kind == "write_config":
            ...
        elif kind == "set_provider_key":
            runtime.set_key(req["provider"], req["key"])
            await ws.send(json.dumps({"kind": "key_set", "provider": req["provider"]}))
        elif kind == "test_provider":
            await handle_test_provider(ws, req)
        elif kind == "read_theses":
            theses = runtime.read_theses(req["ticker"], limit=req.get("limit", 10))
            await ws.send(json.dumps({"kind": "theses", "ticker": req["ticker"], "theses": theses}))
        elif kind == "list_flows":
            flows = list_flows_on_disk()
            await ws.send(json.dumps({"kind": "flow_list", "flows": flows}))
        else:
            await ws.send(json.dumps({"kind": "error", "message": f"unknown kind: {kind}"}))

async def handle_run_flow(ws, req):
    graph = req["graph"]
    inputs = req["inputs"]
    # compile graph → wave plan
    wave_plan = compiler.compile(graph)
    # stream events
    try:
        async for event in runtime.run_custom_flow_stream(
            graph=wave_plan, inputs=inputs,
            default_model=graph["default_model"],
            per_agent_model=extract_per_agent_model(graph),
            depth=graph.get("depth", "STANDARD"),
            compressed=graph.get("compressed", False),
        ):
            await ws.send(json.dumps(event_to_dict(event)))
    except Exception as e:
        await ws.send(json.dumps({"kind": "flow_failed", "reason": str(e)}))

def event_to_dict(event):
    """Serialize a runtime Event dataclass to a JSON dict."""
    # uses dataclasses.asdict + the `kind` ClassVar
    ...
```

### 3.3 `app/bridge/compiler.py` — graph → wave plan (~300 lines)

The compiler takes a `.labourious-flow.json` graph and produces a wave plan: an ordered list of waves, where each wave is a list of agents that can run in parallel (no inter-dependencies within the wave).

```python
def compile(graph: dict) -> list[Wave]:
    """
    Topologically sort the graph's nodes into waves.
    Each wave is a list of (agent_id, model, brief, depends_on) tuples
    that can run in parallel.

    Raises GraphCycleError if the graph has a cycle.
    Raises NoTerminalNodeError if no node has out-degree 0.
    """
    nodes = {n["id"]: n for n in graph["nodes"]}
    edges = graph["edges"]
    # build adjacency
    deps = {nid: set() for nid in nodes}
    rdeps = {nid: set() for nid in nodes}
    for e in edges:
        if e["source"] == e["target"]: continue  # self-loop, skip (caught by cycle check)
        deps[e["target"]].add(e["source"])
        rdeps[e["source"]].add(e["target"])
    # Kahn's algorithm, wave-by-wave
    waves = []
    remaining = set(nodes)
    while remaining:
        ready = [nid for nid in remaining if not (deps[nid] & remaining)]
        if not ready:
            raise GraphCycleError(f"cycle among: {remaining}")
        waves.append(Wave(nodes=[nodes[nid] for nid in ready]))
        remaining -= set(ready)
    return waves
```

Parallel branches within a wave are executed via `ThreadPoolExecutor(max_workers=2)` (the same machinery the runtime uses for f1 wave-3). The compiler just declares the waves; the runtime executes them.

---

## 4. The runtime's new entry point — `run_custom_flow_stream`

Phase 2 adds one function to `docs/runtime/runtime.py`. It mirrors the shape of `run_flow_stream` (which the TUI uses) but takes a compiled wave plan instead of a fixed `flow_id`.

```python
def run_custom_flow_stream(
    graph: dict,                  # the compiled wave plan (from bridge/compiler.py)
    inputs: dict,                 # { "ticker": "NVDA" } or { "tickers": [...] }
    default_model: str,
    per_agent_model: dict[str, str] | None = None,
    depth: str = "STANDARD",
    compressed: bool = False,
    paid_for: list[str] | None = None,
) -> Iterator[Event]:
    """
    Execute a user-built custom graph. Yields the same Event types as
    run_flow_stream. The 10 built-in flows (execute_flow_f1..f10) are
    unaffected — this is additive.
    """
    # 1. emit FlowStarted
    # 2. read prior theses → emit ThesisPriorRead
    # 3. for each wave in graph.waves:
    #      if len(wave) == 1: call_agent(wave[0])  → emit AgentStarted/AgentFinished
    #      else: ThreadPoolExecutor(max_workers=2) → emit interleaved AgentStarted/AgentFinished
    # 4. for each forcer edge encountered: emit DirectiveInjected, re-run upstream, emit ForcerPassComplete
    # 5. emit CostDelta after each agent
    # 6. emit FlowFinished or FlowFailed
    ...
```

This is the **only runtime change** required for the app. The 10 built-in flows continue to work via `run_flow_stream`; the TUI is unaffected.

---

## 5. Tooling and dev workflow

### 5.1 Development

```
# From app/ directory:
npm install                           # install React + React Flow + Zustand + Vite
npm run tauri dev                     # launches the desktop app in dev mode
                                      # (hot-reload on React changes; Rust changes rebuild)

# To run the bridge standalone (for debugging without the app):
cd app/bridge && python sidecar.py    # prints a port; connect with wscat or similar
```

### 5.2 Building

```
npm run tauri build                   # produces .dmg (macOS) / .msi (Windows)
                                      # bundles the Python sidecar via Tauri's sidecar feature
```

The Python sidecar is bundled as a portable Python + `site-packages` directory (per [`STACK-DECISION.md`](STACK-DECISION.md) §Layer 3 — option 2 for dev velocity, consider PyOxidizer for a leaner v2 binary).

### 5.3 Testing

The app inherits the runtime's existing test suite (`docs/runtime/evals/` + `docs/runtime/smokes/`) — they run against the runtime, which the app shares. App-specific tests (Phase 2+):

- **`app/bridge/test_compiler.py`** — graph cycle detection, wave-plan correctness, forcer-edge handling. Target: 30+ assertions.
- **`app/bridge/test_server.py`** — WS message round-trip, event serialization, cancel-flow. Target: 40+ assertions.
- **`app/src/lib/__tests__/graph-validate.test.ts`** — client-side validation (cycle, terminal, key). Target: 20+ assertions.
- **`app/src/lib/__tests__/mock-events.test.ts`** — the Phase 1 mock stream matches the real event protocol shape. Target: 15+ assertions.

The benchmark harness `docs/runtime/benchmarks/run_bench.py` is extended in Phase 2 to include the bridge compiler tests (same pattern as the TUI's smoke pilots).

---

## 6. What this doc doesn't say

- The visual rendering details (node body, citation cards) — see [`SPEC.md`](SPEC.md).
- The graph JSON schema and WS contract — see [`PROTOCOL.md`](PROTOCOL.md).
- The agent-library catalog contents — see [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md).
- The build phases and their acceptance criteria — see [`ROADMAP.md`](ROADMAP.md).
- The stack research (why Tauri over Electron, why React Flow) — see [`STACK-DECISION.md`](STACK-DECISION.md).
