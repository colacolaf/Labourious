# PROTOCOL — the graph JSON schema + WebSocket event bridge contract

> The contract between the app (React + React Flow frontend) and the runtime (Python, via the bundled WS sidecar). The app **produces** a graph (JSON) and **consumes** a stream of events (JSON over WebSocket). The runtime **consumes** the graph and **produces** the event stream.

This file has three parts:

1. **The graph schema** (`.labourious-flow.json`) — what the app saves/loads/exports and what the runtime executes.
2. **The WebSocket bridge protocol** — the messages that cross the WS between the app and the bundled Python sidecar.
3. **The event stream** — the runtime events the app renders, mapped from `docs/runtime/events.py` (the single source of truth).

The runtime's existing `docs/runtime/events.py` is **canonical**. This file documents the JSON-on-the-wire shape of those events for the app consumer; it does not redefine them. Any new event added to `events.py` is automatically a wire event the app must gracefully ignore if unknown (forward-compat, same rule as the TUI).

---

## 1. The graph schema — `.labourious-flow.json`

A saved/loaded/exported graph. The file is the canonical artifact a user shares, imports, or re-runs.

```json
{
  "schema_version": 1,
  "name": "NVDA deep-dive",
  "description": "Senior-analyst + technical + forensic → final-report",
  "created_at": "2026-08-24T12:00:00Z",
  "updated_at": "2026-08-24T12:30:00Z",
  "ticker_input": "NVDA",
  "default_model": "ollama/llama3.3:70b",
  "depth": "STANDARD",
  "compressed": false,
  "nodes": [
    {
      "id": "n1",
      "node_type": "agent",
      "agent_id": "senior-analyst",
      "source": "builtin",
      "model_override": null,
      "position": { "x": 120, "y": 80 },
      "config": {}
    },
    {
      "id": "n2",
      "node_type": "agent",
      "agent_id": "technical",
      "source": "library",
      "library_ref": "technical",
      "model_override": "anthropic/claude-sonnet-4-5",
      "position": { "x": 360, "y": 40 },
      "config": {}
    },
    {
      "id": "n3",
      "node_type": "agent",
      "agent_id": "final-report",
      "source": "builtin",
      "model_override": null,
      "position": { "x": 640, "y": 120 },
      "config": {}
    },
    {
      "id": "f1",
      "node_type": "research_forcer",
      "depth_budget": 1,
      "directive_template": "Find {N} more primary sources for each sub-claim in section '{section}'.",
      "position": { "x": 240, "y": 200 },
      "config": {}
    }
  ],
  "edges": [
    { "id": "e1", "source": "n1", "target": "n2", "type": "passthrough" },
    { "id": "e2", "source": "n1", "target": "n3", "type": "research_forcer", "forcer_node_id": "f1" },
    { "id": "e3", "source": "n2", "target": "n3", "type": "passthrough" }
  ]
}
```

### 1.1 Node object

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique within the graph. React Flow node id. |
| `node_type` | `"agent"` \| `"research_forcer"` | yes | Discriminator. |
| `agent_id` | string | yes if `node_type == "agent"` | The agent's id. For built-ins: one of `orchestrator`, `senior-analyst`, `forensic-accounting`, `devils-advocate`, `final-report`. For library: the library entry's `agent_id`. |
| `source` | `"builtin"` \| `"library"` | yes if `node_type == "agent"` | Where the agent comes from. |
| `library_ref` | string | yes if `source == "library"` | The catalog file name (without `.json`) under `app/agent-library/`. |
| `model_override` | string \| null | no | If set, this node runs on this model; else uses the graph's `default_model`. |
| `position` | `{x: number, y: number}` | yes | Canvas position (React Flow). |
| `config` | object | no | Per-node-type config (Phase 4+). Empty for v1. |

### 1.2 Research-forcer node

A `research_forcer` node is **not an agent** — it has no `agent_id`, no `model_override`, and it doesn't run on its own. It's a directive-injector attached to an edge (via the edge's `forcer_node_id`). On Run, when the upstream agent of that edge finishes, the forcer inspects its envelope, generates a "dig deeper" directive from its `directive_template`, and re-runs the upstream agent with the directive appended to its brief. The re-run's envelope is what flows downstream.

| Field | Type | Required | Notes |
|---|---|---|---|
| `depth_budget` | integer | yes | Max extra passes (0 = passthrough, 1 = one extra pass, max 3). |
| `directive_template` | string | yes | A template with `{N}` and `{section}` placeholders the runtime fills. |

### 1.3 Edge object

| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | string | yes | Unique within the graph. |
| `source` | string | yes | Source node id. |
| `target` | string | yes | Target node id. |
| `type` | `"passthrough"` \| `"research_forcer"` | yes | Discriminator. |
| `forcer_node_id` | string | yes if `type == "research_forcer"` | The forcer node attached to this edge. |

### 1.4 Graph-level fields

| Field | Type | Notes |
|---|---|---|
| `schema_version` | integer | Currently `1`. Bump on breaking schema changes; the app/runtime migrate. |
| `name`, `description` | string | Human-readable. |
| `ticker_input` | string | The ticker(s). Comma-separated for compare graphs (`NVDA, AMD, INTC`). |
| `default_model` | string | The graph's default model; nodes without `model_override` use this. |
| `depth` | `"SCAN"` \| `"STANDARD"` \| `"DEEP"` \| `"COMPRESSED"` | Passed to runtime. |
| `compressed` | boolean | Passed to runtime. |

### 1.5 Validation rules (enforced at compile time, before Run)

1. **No cycles** — the graph must be a DAG. Cycles are rejected with a clear error naming the cycle path.
2. **At least one terminal node** — a node with no outgoing edges. Typically the `final-report`. If none, the graph can't produce a memo.
3. **All `research_forcer` edges reference a valid `forcer_node_id`** — and that forcer node must be of `node_type == "research_forcer"`.
4. **All `library` agents have a valid `library_ref`** — the file must exist under `app/agent-library/`.
5. **`ticker_input` is non-empty** — a graph without a ticker can't run.
6. **`depth_budget ≤ 3`** — caps the forcer's cost.

---

## 2. The WebSocket bridge protocol

The bundled Python sidecar runs a WS server on `127.0.0.1:<port>` (port auto-selected at startup, passed to the app via a Tauri sidecar arg). The app connects on startup and stays connected for the session.

### 2.1 Message envelope

Every WS message (both directions) is a JSON object with a `kind` discriminator:

```json
{ "kind": "<message-type>", ... }
```

### 2.2 App → Sidecar messages

| `kind` | Fields | Purpose |
|---|---|---|
| `hello` | `{ "app_version": "0.1.0", "protocol_version": 1 }` | Sent on connect. Sidecar responds with `hello_ack`. |
| `run_flow` | `{ "graph": <graph-json>, "inputs": { "ticker": "NVDA" } }` | Start a run. Sidecar responds with a stream of events (§3) ending in `flow_finished` or `flow_failed`. |
| `cancel_flow` | `{ "flow_id": "..." }` | Cancel a running flow. Sidecar responds with `flow_cancelled`. |
| `read_config` | `{}` | Request the current `~/.labourious/config.json`. Sidecar responds with `config`. |
| `write_config` | `{ "config": {...} }` | Write `~/.labourious/config.json`. Sidecar responds with `config_written` or `config_error`. |
| `set_provider_key` | `{ "provider": "anthropic", "key": "sk-..." }` | Store a key in the OS keychain (via `keyring`). Sidecar responds with `key_set` or `key_error`. |
| `get_provider_key` | `{ "provider": "anthropic" }` | Read a key from the keychain. Sidecar responds with `key_value` (key redacted to a presence flag, not the actual secret — the app never sees the key). |
| `delete_provider_key` | `{ "provider": "anthropic" }` | Delete a key. Sidecar responds with `key_deleted`. |
| `test_provider` | `{ "provider": "anthropic", "model": "claude-sonnet-4-5" }` | Run the health probe (4-token "ok" prompt). Sidecar streams `test_started` → `test_finished` with status + latency. |
| `read_theses` | `{ "ticker": "NVDA", "limit": 10 }` | Read prior theses. Sidecar responds with `theses`. |
| `list_flows` | `{}` | List `~/.labourious/flows/*.labourious-flow.json`. Sidecar responds with `flow_list`. |

### 2.3 Sidecar → App messages

| `kind` | Fields | Purpose |
|---|---|---|
| `hello_ack` | `{ "runtime_version": "0.1.0", "protocol_version": 1, "providers_available": ["ollama", "anthropic", ...] }` | Response to `hello`. |
| `config` | `{ "config": {...} }` | Response to `read_config`. |
| `config_written` | `{}` | Response to `write_config`. |
| `config_error` | `{ "error": "..." }` | Response to `write_config` on failure. |
| `key_set` | `{ "provider": "anthropic" }` | Response to `set_provider_key`. |
| `key_value` | `{ "provider": "anthropic", "has_key": true }` | Response to `get_provider_key` — never includes the actual key. |
| `key_deleted` | `{ "provider": "anthropic" }` | Response to `delete_provider_key`. |
| `key_error` | `{ "provider": "anthropic", "error": "..." }` | Keychain failure. |
| `test_started` | `{ "provider": "anthropic" }` | Health probe started. |
| `test_finished` | `{ "provider": "anthropic", "status": "OK", "latency_ms": 412 }` | Health probe finished. `status`: `OK` / `FAIL` / `AUTH_MISSING` / `TIMEOUT` / `UNREACHABLE`. |
| `theses` | `{ "ticker": "NVDA", "theses": [...] }` | Response to `read_theses`. |
| `flow_list` | `{ "flows": [{ "name": "...", "path": "...", "updated_at": "..." }] }` | Response to `list_flows`. |
| `flow_cancelled` | `{ "flow_id": "..." }` | Response to `cancel_flow`. |
| `error` | `{ "message": "...", "code": "..." }` | Generic error (malformed message, unknown kind, internal exception). |

Plus the **event stream** messages (one per runtime `Event`) — see §3.

### 2.4 Ordering guarantees

- `run_flow` triggers a stream of events ending in exactly one `flow_finished` or `flow_failed`. The app must handle both as terminal.
- Events arrive in order within a single flow. Parallel-agent events interleave (no ordering guarantee *across* agents, only *within* one agent).
- `cancel_flow` is best-effort: if the flow already finished, the sidecar responds `flow_cancelled` with the original `flow_id` but no re-execution.
- The app must gracefully ignore unknown `kind` values (forward-compat, same rule as the TUI's event handling).

### 2.5 Connection lifecycle

- On disconnect, the app shows the "runtime disconnected" banner and retries every 3s.
- On reconnect, the app sends `hello` again; the sidecar treats it as a fresh session (no flow state carried over — if a flow was running when the connection dropped, the sidecar continues it to completion but the app has lost the event stream; the user must re-run).
- The sidecar process is spawned per app session (no daemon). When the app quits, the sidecar receives `SIGTERM` and exits.

---

## 3. The event stream — runtime events on the wire

The runtime emits `Event` dataclasses (defined in `docs/runtime/events.py`, the single source of truth). The bridge serializes each to a JSON WS message with `kind` = the dataclass's `kind` ClassVar. The app renders each.

### 3.1 Flow lifecycle (from `docs/runtime/events.py`)

| `kind` | Fields (JSON wire shape) | When emitted |
|---|---|---|
| `flow_started` | `flow_id`, `tickers` (array), `ticker_join` (string), `thesis_register_snapshot` (array), `depth`, `compressed` | First event of a run. |
| `flow_finished` | `flow_id`, `final_envelope` (the final-report JSON), `total_cost_usd_estimate` | Last event of a successful run. |
| `flow_failed` | `flow_id`, `reason`, `failed_agent_id` (or null), `partial_envelopes` (map) | When the run can't complete. |

### 3.2 Agent lifecycle

| `kind` | Fields | When emitted |
|---|---|---|
| `agent_started` | `agent_id`, `model`, `depth`, `compressed` | Just before the model call. |
| `agent_chunk` | `agent_id`, `delta` | During streaming (0 or 1 per agent in v1; N once SSE streaming ships). |
| `agent_finished` | `agent_id`, `envelope`, `wallclock_s`, `in_tokens`, `out_tokens`, `cost_usd_estimate` | After the model call returns. |
| `agent_failed` | `agent_id`, `error` | When the agent crashes or times out. |

### 3.3 Connector / tool events

| `kind` | Fields | When emitted |
|---|---|---|
| `connector_requested` | `tool`, `query`, `requested_by_agent` | When an agent's output indicates a tool need. |
| `connector_completed` | `tool`, `status`, `note`, `as_of`, `data_summary`, `requested_by_agent` | When a tool call returns. `status`: `SUCCESS` / `PARTIAL` / `FAILED` / `EMPTY`. |
| `connector_failed` | `tool`, `error`, `requested_by_agent` | When a tool is unreachable. |

### 3.4 Thesis register events

| `kind` | Fields | When emitted |
|---|---|---|
| `thesis_prior_read` | `ticker`, `prior_theses` (array) | At flow start, for RELEVANT HISTORY. |
| `thesis_written` | `ticker`, `thesis_id`, `version`, `thesis_text`, `conviction`, `bottom_line`, `evidence_urls` | When a successful run writes a new versioned row. |
| `catalyst_added` | `ticker`, `event`, `expected_date`, `what_to_watch` | When a flow's next-three-questions are written as catalysts. |
| `catalyst_resolved` | `ticker`, `catalyst_id`, `resolved_date`, `outcome` | When f4 (earnings review) writes a resolution. |

### 3.5 Cost

| `kind` | Fields | When emitted |
|---|---|---|
| `cost_delta` | `agent_id`, `in_tokens`, `out_tokens`, `cost_usd_estimate`, `cumulative_in`, `cumulative_out`, `cumulative_cost` | After each `agent_finished`. |

### 3.6 New events reserved for the app (Phase 4 — research-forcer)

The research-forcer's directive-injection step emits two new events (added to `docs/runtime/events.py` in Phase 4, additive, non-breaking):

| `kind` | Fields | When emitted |
|---|---|---|
| `directive_injected` | `forcer_node_id`, `upstream_agent_id`, `directive` (string), `pass_number` (1 = first re-run, 2 = second, …) | When the forcer generates a directive and re-runs the upstream agent. |
| `forcer_pass_complete` | `forcer_node_id`, `upstream_agent_id`, `pass_number`, `depth_budget` (remaining) | When an extra pass finishes; the forcer decides whether to do another. |

The app renders these as a badge on the forcer's edge: `⚡ pass 1/1` or `⚡ pass 2/3`.

---

## 4. The runtime's new entry point — `run_custom_flow_stream`

Phase 2 adds one new function to `docs/runtime/runtime.py`, alongside the existing `execute_flow_f1` … `execute_flow_f10`:

```python
def run_custom_flow_stream(
    graph: dict,                # the parsed .labourious-flow.json
    inputs: dict,               # { "ticker": "NVDA" } or { "tickers": ["NVDA", "AMD"] }
    default_model: str,
    per_agent_model: dict[str, str] | None = None,  # { agent_id: model } from node overrides
    depth: str = "STANDARD",
    compressed: bool = False,
    paid_for: list[str] | None = None,              # hybrid routing (agents to run on paid)
) -> Iterator[Event]:
    """Execute a user-built graph. Yields the same Event types as run_flow_stream."""
```

Internally, the graph compiler (in the bridge, `app/bridge/compiler.py`) takes the graph JSON and produces a wave plan: an ordered list of `(agent_id, model, brief, depends_on)` tuples, with parallel branches grouped. The runtime executes the wave plan via `call_agent` + `ThreadPoolExecutor` for parallel branches, yielding the same events the TUI's `run_flow_stream` does.

The 10 built-in flows (`execute_flow_f1` … `f10`) are **unaffected** — they remain the TUI's path. `run_custom_flow_stream` is additive.

---

## 5. Schema versioning

- **Graph schema** (`schema_version` in `.labourious-flow.json`): currently `1`. Breaking changes bump the version; the app/runtime migrate old files on load.
- **WS protocol** (`protocol_version` in `hello` / `hello_ack`): currently `1`. Breaking changes bump the version; the app and sidecar negotiate on connect.
- **Event kinds**: adding new kinds is non-breaking (forward-compat). Removing a kind is breaking. The app must gracefully ignore unknown kinds, same as the TUI.

---

## 6. What this protocol doesn't say

- The visual rendering of events (citations cards, activity rows, memo sections) — see [`SPEC.md`](SPEC.md) §5.
- The agent-library catalog contents — see [`AGENT-LIBRARY.md`](AGENT-LIBRARY.md).
- The bridge's Python implementation — see [`IMPLEMENTATION.md`](IMPLEMENTATION.md) §3.
