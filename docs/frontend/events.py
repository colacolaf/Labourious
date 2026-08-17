"""
events.py (frontend) — Re-export runtime events to give the TUI a single import path.

Kept tiny on purpose: the schema lives in `runtime/events.py` (single source of truth).
The TUI does not need a separate copy of the dataclasses; it needs a stable import
path and the list of valid kinds so it can ignore unknown ones (forward compat).

Mirrors `docs/frontend/PROTOCOL.md`.
"""

from __future__ import annotations

# Re-export everything from the runtime so the TUI has one stable import.
from runtime.events import (  # type: ignore  # noqa: F401
    Event,
    FlowStarted, FlowFinished, FlowFailed,
    AgentStarted, AgentChunk, AgentFinished, AgentFailed,
    ConnectorRequested, ConnectorCompleted, ConnectorFailed,
    ThesisPriorRead, ThesisWritten, CatalystAdded, CatalystResolved,
    CostDelta,
    ALL_EVENT_TYPES,
    event_kind,
)


# Forward compatibility: any future runtime that emits an event whose subclass
# isn't imported here is gracefully ignored (the TUI must never crash on a new
# event type — see PROTOCOL.md §4).
KNOWN_KINDS = frozenset(t.kind for t in ALL_EVENT_TYPES)


def is_known(event: Event) -> bool:
    """True if this event type is recognised by the current TUI build."""
    return getattr(event, "kind", "") in KNOWN_KINDS
