# IMPLEMENTATION — file plan, line budgets, and runtime.py changes

> What gets built, in what order, with rough size budgets. Pairs with [`SPEC.md`](SPEC.md) (what to build), [`SCREENS.md`](SCREENS.md) (when each state lives), [`PROTOCOL.md`](PROTOCOL.md) (the event contract).

This is *not* a sprint plan; it's a **budget plan** so each file ships at the right size. A file that's under budget is good; a file that's over budget is a code-smell signal (extract).

## File layout

```
docs/frontend/
├── README.md            # the directory's role (already exists)
├── SPEC.md              # TUI behaviour (already exists)
├── SCREENS.md           # state machine (already exists)
├── PROTOCOL.md          # the event protocol (already exists)
├── IMPLEMENTATION.md    # this file
│
├── app.py               # the Textual App: top-level orchestration
├── style.tcss           # CSS-style theme (Textual styling)
├── keys.py              # keybindings + command palette commands
├── events.py            # Event dataclasses (mirror of runtime side; pick a home)
│
├── screens/
│   ├── __init__.py
│   ├── chat.py          # the chat screen (1.a-1.d)
│   ├── settings.py      # the settings modal (screen 2)
│   └── history.py       # the history modal (screen 3)
│
└── widgets/
    ├── __init__.py
    ├── message_bubble.py
    ├── activity_panel.py
    ├── cost_widget.py
    ├── diff_widget.py
    ├── citation_chip.py
    └── connection_banner.py
```

Total budget: ~1500 lines of Python + ~150 lines of CSS.

## Per-file budget

| File | Lines | What it contains |
|------|-------|------------------|
| `frontend/app.py` | ~120 | `LabouriousApp(App)` — sets up bindings, mounts `ChatScreen`, registers the runtime worker. |
| `frontend/style.tcss` | ~150 | Light-on-text CSS: palette, sidebar widths, bubble backgrounds, citation chip styles. |
| `frontend/keys.py` | ~50 | Bindings + command palette commands (`/help`, `/flow`, `/ticker`, `/model`, `/paid-for`, `/settings`, `/history`, `/quit`). |
| `frontend/events.py` | ~120 | The dataclasses (mirror or import of `runtime/events.py`). |
| `frontend/screens/chat.py` | ~280 | The chat screen. Owns the message-bubble log, the activity panel, the cost widget, the prompt input. Listens to stream events; updates widgets reactively. |
| `frontend/screens/settings.py` | ~150 | Settings modal. Reads/writes `~/.labourious/config.json`. Tabs: Providers / Default Model / Per-agent / Connectors / Hybrid / Defaults. |
| `frontend/screens/history.py` | ~120 | History modal. Reads `docs/runtime/thesis_register/theses.db`. Two-pane browser. |
| `frontend/widgets/message_bubble.py` | ~100 | Single bubble: header (role/timing/confidence), streaming body via `Markdown.update()`, footer chips. |
| `frontend/widgets/activity_panel.py` | ~80 | Sidebar's per-agent row: state icon, agent id, wallclock, tokens. |
| `frontend/widgets/cost_widget.py` | ~50 | Three small lines (in/out/est) updating per `CostDelta`. |
| `frontend/widgets/diff_widget.py` | ~80 | Collapsible side-by-side prior vs. new thesis; only if `ThesisPriorRead` populates the data. |
| `frontend/widgets/citation_chip.py` | ~70 | Footer chip `[N citations]` → modal `CitationModalScreen`. |
| `frontend/widgets/connection_banner.py` | ~40 | Red/yellow banner for missing API key or unreachable tool. |
| **Total** | **~1410** |  |

## Order of implementation

P1 (must ship for f1 end-to-end + TUI demo):

1. `frontend/events.py` — the schema (parallel to or imported from runtime).
2. `frontend/side/connection_banner.py` — simple, the welcome state uses it.
3. `frontend/widgets/message_bubble.py` — the fundamental display.
4. `frontend/widgets/activity_panel.py` — paired with chat screen.
5. `frontend/widgets/cost_widget.py` — paired with activity panel.
6. `frontend/screens/chat.py` — pulls the above into a screen.
7. `frontend/keys.py` — the bindings + commands.
8. `frontend/app.py` — wiring + entrypoint.

P2 (Settings + History + polish):

9. `frontend/side/settings.py` — Settings modal. Requires `~/.labourious/config.json` schema understanding.
10. `frontend/side/history.py` — History modal.
11. `frontend/widgets/citation_chip.py` — citation modal.
12. `frontend/widgets/diff_widget.py` — side-by-side.
13. `frontend/style.tcss` — finalize theme; one round of polish.

## Runtime changes (`docs/runtime/runtime.py`)

Add **without changing** today's CLI surface:

```python
# In runtime/events.py (new):
@dataclass(frozen=True)
class FlowStarted: ...
@dataclass(frozen=True)
class AgentStarted: ...
@dataclass(frozen=True)
class AgentChunk: ...
@dataclass(frozen=True)
class AgentFinished: ...
@dataclass(frozen=True)
class FlowFinished: ...
@dataclass(frozen=True)
class FlowFailed: ...
# ... see PROTOCOL.md for the full list

# In runtime/runtime.py:
def run_flow_stream(flow_id, inputs, model, paid_for) -> Iterator[Event]:
    """The new public entrypoint. Same business logic as execute_flow_*();
       wraps each agent call with emit(AgentStarted) / emit(AgentFinished)."""
    yield FlowStarted(flow_id=flow_id, tickers=inputs.get("ticker"), ...)
    register = ThesisRegister()
    yield ThesisPriorRead(ticker=..., prior_theses=register.read_thesis(...))
    # ... each call_agent() now wraps the AgentStarted/Finished emits
    # ... each tool call emits ConnectorRequested/Completed
    # ... on success: ThesisWritten + CatalystAdded as appropriate
    # ... final event
    yield FlowFinished(flow_id=flow_id, final_envelope=...)
```

**Backward compat**: keep `main()` returning the markdown to stdout. Add a new `main_stream()` that wraps `run_flow_stream` for the TUI (or have the TUI import `run_flow_stream` directly).

**Cost**: this refactor is the only runtime-side change. The existing test fixtures (the dry-run output, the 5 evals) remain unchanged because the refactor preserves today's signatures.

## Configuration model

Reference [`PROTOCOL.md` Appendix A](PROTOCOL.md#6-appendix-a---labouriousconfigjson-schema-canonical) for the schema. Concretely:

- **File is canonical.** The runtime reads `~/.labourious/config.json` at startup; the TUI's `SettingsScreen` writes to it.
- **API keys live in env.** The file never contains actual keys; it references env-var names.
- **Per-agent overrides.** Hybrid routing is just a `per_agent_model` override on `final-report`.

## CLI ↔ TUI parity

Both entrypoints get to use the same config:

| Task | CLI | TUI |
|---|---|---|
| Run f1 on NVDA | `python docs/runtime/runtime.py --flow f1 --ticker NVDA --model ollama/llama3.3:70b` | `/flow f1 /ticker NVDA /model ollama/llama3.3:70b` |
| Edit config | `vim ~/.labourious/config.json` | `[s]` Settings modal |
| See prior theses | `python docs/runtime/thesis_register/register.py show NVDA` | `[h]` History → `NVDA` |
| Re-run last prompt | cursor-up + Enter (shell history) | `Ctrl+R` |

Both read the same `~/.labourious/config.json`. Both write the same `docs/runtime/thesis_register/theses.db`. The TUI is sugar over the CLI's surface, **not a new system**.

## Pyproject or requirements.txt?

Add to a single `docs/runtime/requirements.txt`:

```
textual>=3.7
rich>=13
keyring>=24        # for the OS-keychain Settings flow
tomli>=2           # config.json schema validation
```

(Plus the existing `yfinance` and similar.)

If the project grows a `pyproject.toml` later, those dependencies move there. For now, `requirements.txt` keeps the surface minimal.

## What this file doesn't say

- *Why* TUI over a browser — [`../FRONTEND-DECISION.md`](../FRONTEND-DECISION.md).
- *What* the TUI does — [`SPEC.md`](SPEC.md).
- *When* each state lives — [`SCREENS.md`](SCREENS.md).
- *How* runtime ↔ TUI talk — [`PROTOCOL.md`](PROTOCOL.md).
