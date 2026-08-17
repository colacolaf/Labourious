"""
events.py — Typed Event dataclasses (single source of truth for the runtime/TUI protocol).

Mirrors `docs/frontend/PROTOCOL.md` exactly. The runtime emits these; the TUI consumes them.
Adding a new event is non-breaking (TUI must gracefully ignore unknown kinds).
Removing an event is breaking (avoid).

Each event is `@dataclass(frozen=True)` and JSON-serializable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar


# --------------------------------------------------------------------------- #
# Base
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Event:
    """Base class. Every concrete event has a stable `kind` discriminator."""
    kind: ClassVar[str] = ""  # overridden by subclass


# --------------------------------------------------------------------------- #
# 1. Flow lifecycle
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class FlowStarted(Event):
    kind: ClassVar[str] = "flow_started"
    flow_id: str
    tickers: list[str]
    ticker_join: str
    thesis_register_snapshot: list[dict[str, Any]]  # prior theses from ThesisRegister.read_thesis
    depth: str = "STANDARD"
    compressed: bool = False


@dataclass(frozen=True)
class FlowFinished(Event):
    kind: ClassVar[str] = "flow_finished"
    flow_id: str
    final_envelope: dict[str, Any]   # the final-report JSON envelope
    total_cost_usd_estimate: float = 0.0


@dataclass(frozen=True)
class FlowFailed(Event):
    kind: ClassVar[str] = "flow_failed"
    flow_id: str
    reason: str
    failed_agent_id: str | None
    partial_envelopes: dict[str, dict[str, Any]] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 2. Agent lifecycle
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class AgentStarted(Event):
    kind: ClassVar[str] = "agent_started"
    agent_id: str
    model: str
    depth: str
    compressed: bool


@dataclass(frozen=True)
class AgentChunk(Event):
    kind: ClassVar[str] = "agent_chunk"
    agent_id: str
    delta: str  # a chunk of streamed text. Future: many per agent; v1: emits 1 per agent.


@dataclass(frozen=True)
class AgentFinished(Event):
    kind: ClassVar[str] = "agent_finished"
    agent_id: str
    envelope: dict[str, Any]   # parsed JSON envelope
    wallclock_s: float
    in_tokens: int
    out_tokens: int
    cost_usd_estimate: float


@dataclass(frozen=True)
class AgentFailed(Event):
    kind: ClassVar[str] = "agent_failed"
    agent_id: str
    error: str


# --------------------------------------------------------------------------- #
# 3. Connector / tool events (reserved for v1.5+ tool-feeding integrations)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ConnectorRequested(Event):
    kind: ClassVar[str] = "connector_requested"
    tool: str
    query: str
    requested_by_agent: str


@dataclass(frozen=True)
class ConnectorCompleted(Event):
    kind: ClassVar[str] = "connector_completed"
    tool: str
    status: str  # SUCCESS | PARTIAL | FAILED | EMPTY
    note: str
    as_of: str
    data_summary: str


@dataclass(frozen=True)
class ConnectorFailed(Event):
    kind: ClassVar[str] = "connector_failed"
    tool: str
    error: str


# --------------------------------------------------------------------------- #
# 4. Thesis register events
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ThesisPriorRead(Event):
    kind: ClassVar[str] = "thesis_prior_read"
    ticker: str
    prior_theses: list[dict[str, Any]]


@dataclass(frozen=True)
class ThesisWritten(Event):
    kind: ClassVar[str] = "thesis_written"
    ticker: str
    thesis_id: int
    version: str
    thesis_text: str
    conviction: int
    bottom_line: dict[str, Any]
    evidence_urls: list[str]


@dataclass(frozen=True)
class CatalystAdded(Event):
    kind: ClassVar[str] = "catalyst_added"
    ticker: str
    event: str
    expected_date: str
    what_to_watch: str


@dataclass(frozen=True)
class CatalystResolved(Event):
    kind: ClassVar[str] = "catalyst_resolved"
    ticker: str
    catalyst_id: int
    resolved_date: str
    outcome: str


# --------------------------------------------------------------------------- #
# 5. Cost
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CostDelta(Event):
    kind: ClassVar[str] = "cost_delta"
    agent_id: str
    in_tokens: int
    out_tokens: int
    cost_usd_estimate: float
    cumulative_in: int
    cumulative_out: int
    cumulative_cost: float


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def event_kind(event: Event) -> str:
    """Read the discriminator. Safe even if event.__class__ was used directly."""
    return getattr(event, "kind", "") or type(event).__name__.lower()


ALL_EVENT_TYPES = (
    FlowStarted, FlowFinished, FlowFailed,
    AgentStarted, AgentChunk, AgentFinished, AgentFailed,
    ConnectorRequested, ConnectorCompleted, ConnectorFailed,
    ThesisPriorRead, ThesisWritten, CatalystAdded, CatalystResolved,
    CostDelta,
)
