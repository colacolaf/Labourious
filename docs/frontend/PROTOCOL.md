# PROTOCOL — what the runtime emits, what the TUI consumes

> The contract between `docs/runtime/runtime.py` and `docs/frontend/app.py`. Today the runtime's `main()` flattens everything to a markdown file; tomorrow it yields a stream of typed events the TUI consumes.

The protocol is **a Python iterator over typed `Event` objects** when both sides run in-process. The same iterator interface becomes a JSON-over-stdout / IPC boundary if we ever split the runtime into a separate process (career-defer-grade refactor; not on the v1 path).

## 1. The iterator interface

The runtime exposes:

```python
def run_flow_stream(flow_id: str, inputs: dict, model: str, paid_for: list[str] | None = None) -> Iterator[Event]:
    """Yields events as the flow progresses. Always completes (with a final `flow_finished` or `flow_failed` event)."""
```

The TUI calls it inside an `asyncio` task and renders each event:

```python
async for event in run_flow_stream(flow_id, inputs, model):
    if isinstance(event, AgentStarted):  activity_panel.mark_running(event.agent_id)
    if isinstance(event, AgentChunk):    message_bubbles[event.agent_id].append(event.delta)
    ...
```

Synchronous iterator → `asyncio` is fine: the existing runtime is sync (it makes HTTP calls via `urllib`), and the TUI wraps the iterator in `asyncio.to_thread()` or in a Textual `Worker` (Textual supports both).

## 2. Event types

All events live in `frontend/events.py` (or `runtime/events.py` if we want the runtime to own the schema). Each event is a `@dataclass(frozen=True)` with a small, JSON-serializable payload.

### 2.1 Flow lifecycle

| Event | Fields | When emitted |
|---|---|---|
| `FlowStarted` | `flow_id`, `tickers`, `ticker_join` (str), `thesis_register_snapshot` (list of prior theses) | First event of a run. |
| `FlowFinished` | `flow_id`, `final_envelope` (the JSON envelope from the final-report agent) | Last event of a successful run. |
| `FlowFailed` | `flow_id`, `reason`, `failed_agent_id` (or None), `partial_envelopes` (map agent_id → envelope for everything that completed before failure) | When the run can't complete. |

### 2.2 Agent lifecycle

| Event | Fields | When emitted |
|---|---|---|
| `AgentStarted` | `agent_id`, `model`, `depth`, `compressed` | Just before the model call. |
| `AgentChunk` | `agent_id`, `delta` (a chunk of the model's streamed output) | During streaming. (Future: when we move to LLMs' SSE mode. For now, single-chunk per agent.) |
| `AgentFinished` | `agent_id`, `envelope` (parsed JSON envelope), `wallclock_s`, `in_tokens`, `out_tokens`, `cost_usd_estimate` | After the model call returns. |

### 2.3 Connector / tool events

| Event | Fields | When emitted |
|---|---|---|
| `ConnectorRequested` | `tool` (e.g. `sec_edgar`), `query` (sanitized), `requested_by_agent` | When the senior-analyst's output indicates a tool need. **Future** — runtime knows the schema but doesn't yet feed it to the model. |
| `ConnectorCompleted` | `tool`, `status` (`SUCCESS | PARTIAL | FAILED | EMPTY`), `note`, `as_of`, `data_summary` (a short string summary suitable for log) | When a tool call returns. |
| `ConnectorFailed` | `tool`, `error` | When a tool is unreachable. |

### 2.4 Thesis register events

| Event | Fields | When emitted |
|---|---|---|
| `ThesisPriorRead` | `ticker`, `prior_theses` (a list of `(date, thesis_text, conviction, bottom_line, version)` rows from `read_thesis(ticker, since=14d)`) | At flow start, for RELEVANT HISTORY. |
| `ThesisWritten` | `ticker`, `thesis_id`, `version`, `thesis_text`, `conviction`, `bottom_line`, `evidence_urls` | When a successful run writes a new versioned row. |
| `CatalystAdded` | `ticker`, `event`, `expected_date`, `what_to_watch` | When a flow's next-three-questions are written as catalysts (v1.5+). |
| `CatalystResolved` | `ticker`, `catalyst_id`, `resolved_date`, `outcome` | When f4 (earnings review) writes a resolution. |

### 2.5 Cost

| Event | Fields | When emitted |
|---|---|---|
| `CostDelta` | `agent_id`, `in_tokens`, `out_tokens`, `cost_usd_estimate`, `cumulative_in`, `cumulative_out`, `cumulative_cost` | After each `AgentFinished`. |

## 3. Ordering guarantees

For a successful run:

```
FlowStarted
  → loop of AgentStarted | AgentChunk* (future) | AgentFinished | ConnectorRequested | ConnectorCompleted (per agent)
  → FlowFinished
```

The runtime **must** emit `FlowStarted` first and `FlowFinished`/`FlowFailed` last. Between those, the per-agent events are emitted in the order they happen. The TUI is allowed to assume:

- Every `AgentStarted` is followed by exactly one `AgentFinished`.
- A `FlowFailed` carries a `partial_envelopes` map so the TUI can render a "what we got before the failure" view.
- `AgentChunk*` is currently 0-N (emitted 0 or 1 times for v1; will become N for full streaming).

## 4. Schema versioning

The events are shape-stable. Adding new events is non-breaking; **the TUI must gracefully ignore unknown event types** (forward compatibility, so future runtime versions add new events without breaking old TUI versions).

```python
@dataclass(frozen=True)
class Event: ...  # base class with a `kind: str` discriminator

@dataclass(frozen=True)
class AgentStarted(Event):
    kind: ClassVar[str] = "agent_started"
    agent_id: str
    ...
```

The TUI's renderer does:

```python
if event.kind == "agent_started":   ...
elif event.kind == "agent_finished": ...
else: pass  # forward-compatible: ignore unknown events
```

Backwards compatibility: removing events is a breaking change. **Avoid the removal.**

## 5. State the TUI holds

The TUI is **the rendering layer**. It does **not** persist state — every reload reads:

- `~/.labourious/config.json` → providers, models, hybrid routing, depth/compressed defaults
- `docs/runtime/thesis_register/theses.db` → prior theses
- `docs/runtime/.runs/<run_id>/final_envelope.json` → last-run result (for the "press Ctrl+R to re-run" affordance)

The TUI only holds in-memory state for the *current* chat session's transcript (a list of message bubbles, fresh on every `Ctrl+L`).

This is deliberate: **the runtime + the SQLite register are the persistent state.** The TUI is stateless across restarts. This makes the system robust — a TUI crash doesn't lose data, and you can swap TUI implementations without losing anything.

## 6. Appendix A — `~/.labourious/config.json` schema (canonical)

The Settings screen edits this file. The runtime reads it at startup. **The file is the source of truth.**

```json
{
  "version": 1,
  "providers": {
    "anthropic": { "base_url": "https://api.anthropic.com", "api_key_env": "ANTHROPIC_API_KEY" },
    "ollama":    { "base_url": "http://localhost:11434" },
    "groq":      { "base_url": "https://api.groq.com/openai/v1", "api_key_env": "GROQ_API_KEY" },
    "openrouter":{ "base_url": "https://openrouter.ai/api/v1", "api_key_env": "OPENROUTER_API_KEY" }
  },
  "default_model": "ollama/llama3.3:70b",
  "per_agent_model": {
    "final-report": "anthropic/claude-sonnet-4-5"
  },
  "hybrid_routing": {
    "paid_for": ["final-report"]
  },
  "connectors": {
    "sec_edgar":   { "provider": "sec_edgar",         "user_agent": "Labourious <[email protected]>" },
    "news":        { "provider": "google_rss" },
    "market_data": { "provider": "yfinance",          "fred_api_key_env": "FRED_API_KEY" },
    "web_fetch":   { "provider": "web_fetch" }
  },
  "defaults": { "depth": "STANDARD", "compressed": false },
  "thesis_register_db_path": "docs/runtime/thesis_register/theses.db",
  "memory": {
    "history_dir": "~/.labourious/history/"
  }
}
```

Notes:
- API keys live in **environment variables** named by `api_key_env`. The runtime reads them via `os.environ`; the file never contains actual keys.
- `per_agent_model` overrides the default model for a specific agent (used today for hybrid routing — `final-report` gets Sonnet even when the default is a free model).
- `version: 1` is the schema version. Future breaking changes bump the version and the runtime reads/migrates accordingly.

## 7. Appendix B — the runtime's exact contract surface for v1

For the v1 TUI, the runtime only needs:

| Function | Purpose |
|---|---|
| `run_flow_stream(flow_id, inputs, model, paid_for)` → `Iterator[Event]` | The event iterator. |
| `load_config() → Config` | Reads `~/.labourious/config.json` (defaults if missing). |
| `ThesisRegister(...)` | Already in `docs/runtime/thesis_register/register.py` — used for read_prior/write/diff APIs. |

Everything else the TUI sees comes through `Event` subclasses. Adding more events is additive; removing events is breaking.

## 8. What this file doesn't say

- Per-widget rendering details (that's `SPEC.md`).
- State transitions (that's `SCREENS.md`).
- File structure & runtime.py changes (that's `IMPLEMENTATION.md`).
