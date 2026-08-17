# docs/frontend/ — what the user chats with

> The Python TUI that lets a user run the Analyst's Bench interactively. This directory is **specs**, not code — the runtime under `docs/runtime/` does the work; the TUI consumes its events.

The TUI is the **only** surface the user sees. The CLI (`python docs/runtime/runtime.py ...`) is the bare equivalent — no UI. The TUI is what makes it usable.

## What's in this directory

| File | Purpose |
|------|---------|
| [`README.md`](README.md) | this file; the index |
| [`SPEC.md`](SPEC.md) | the TUI's components, layout, screen behavior |
| [`SCREENS.md`](SCREENS.md) | the state machine + screen shapes |
| [`PROTOCOL.md`](PROTOCOL.md) | the runtime → TUI event protocol |
| [`IMPLEMENTATION.md`](IMPLEMENTATION.md) | file plan with line budgets + runtime.py changes |

Plus two stub subdirs (`screens/`, `widgets/`) reserved for the actual Python modules implementing the spec.

## What lives here, what doesn't

**In scope for this directory:** documentation about the TUI's structure, screens, and behavior. The specs enough that an implementer can build the TUI from these docs alone.

**Out of scope for this directory:** the TUI's actual Python code (lives in `docs/frontend/screens/*.py` and `docs/frontend/widgets/*.py` once written), the runtime (lives in `docs/runtime/`), prompt text (lives in `docs/prompts/`).

## Why this is a separate directory from `docs/runtime/`

The TUI is **the user's interface** — what they interact with. The runtime is **the system's machine** — what produces results. Different audiences (the user vs. the developer writing/improving the system) and different change cycles (UI polish vs. agent quality).

The connection between them is the **event protocol** in [`PROTOCOL.md`](PROTOCOL.md). The runtime becomes an event-emitting library; the TUI consumes those events and renders them. Today, that contract is implicit (the runtime writes a markdown file). Tomorrow, the contract is explicit (the runtime yields a Python iterator of typed events).

## When to add a doc to this directory

Add a doc here when:

1. **A new screen is added** (e.g. flows-browser screen) — add a section to [`SCREENS.md`](SCREENS.md) describing it. New code goes in `screens/<name>.py`.
2. **A widget is added** (e.g. citation-compare widget) — add a section to [`SPEC.md`](SPEC.md) describing it. New code goes in `widgets/<name>.py`.
3. **The runtime ↔ TUI protocol changes** (a new event type) — update [`PROTOCOL.md`](PROTOCOL.md). The runtime side updates its iterator; the TUI side updates its consumer.
4. **The TUI is wired to a different runtime transport** (e.g. becomes a separate process communicating over IPC) — that's a bigger change, write a new doc.

Don't add a doc here for every UI tweak. The spec docs are intended to be stable across TUI iterations.

## See also

- [`../FRONTEND-DECISION.md`](../FRONTEND-DECISION.md) — the research + decision that chose TUI over Electron / local web / etc.
- [`../ARCHITECTURE.md`](../ARCHITECTURE.md) — the system architecture (now updated to reflect TUI).
- [`../ROADMAP.md`](../ROADMAP.md) — TUI is a P0/P1 item; see the build order.
