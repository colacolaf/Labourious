"""
run_tool_stream.py — Streaming entrypoint for a single tool invocation.

`call_tool(...)` is the canonical way to fire a connector from anywhere, and
its `emit_event=` callback already drives the chat strip. But the TUI
consumes *yields* — see `runtime.run_flow_stream`. This module is the
parallel-yielding version: a generator that yields the same three
Connector* events the runtime emits, so the existing TUI handler routes
them with zero extra wiring on the chat side.

Future: a flow with tool-feeding directives could *also* wrap any
[TOOL: ...] directives the orchestrator emits into `run_tool_stream`
yields — that's the v1.5+ scope per events.py §3. For now, `run_tool_stream`
is wired to a CLI flag so the user can verify end-to-end wiring.
"""

from __future__ import annotations

from typing import Any, Iterator, Mapping

from .call_tool import call_tool
from .events import ConnectorCompleted, ConnectorFailed, ConnectorRequested


def run_tool_stream(
    tool_id: str,
    requested_by_agent: str,
    *,
    method: str | None = None,
    args: Mapping[str, Any] | None = None,
    requested_by_user: bool = False,
) -> Iterator[Any]:
    """Yield the Connector* events a tool call emits.

    The yield order matches the TUI's expectation:
      1. `ConnectorRequested` — strip starts the spinner
      2. `ConnectorCompleted` *or* `ConnectorFailed` — strip lands the chip
    """
    events_out: list[Any] = []

    def _emit(ev: Any) -> None:
        events_out.append(ev)

    call_tool(
        tool_id=tool_id,
        requested_by_agent=requested_by_agent,
        emit_event=_emit,
        method=method,
        args=args,
    )

    while events_out:
        yield events_out.pop(0)
