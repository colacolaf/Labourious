"""
activity_panel.py — the sidebar's per-agent status list.

One row per agent. Each row is a small Vertical containing:
  - a header Static (the agent_id + divider)
  - a RichLog with a single one-line body showing status icon + wallclock

RichLog-based body to avoid the Static-+-str-update layout-versioning issue
in Textual 3.7.

The chat screen calls `.mark_running(agent_id)` / `.mark_finished(agent_id, ...)`
as AgentStarted / AgentFinished events flow in.
"""

from __future__ import annotations

from textual.containers import Container, Vertical
from textual.widgets import RichLog, Static


AGENT_IDS: list[str] = [
    "orchestrator",
    "senior-analyst",
    "forensic-accounting",
    "devils-advocate",
    "final-report",
]

_STATE_ICON = {
    "queued":  "○",
    "running": "◐",
    "done":    "●",
    "failed":  "✗",
    "skipped": "–",
}


class _AgentRow(Vertical):
    """Single row: header (agent_id) + one-line RichLog body."""

    def __init__(self, agent_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent_id = agent_id
        self.state = "queued"
        self.wallclock_s: float | None = None
        self.add_class("activity-row")
        self.add_class(f"row-{agent_id}")
        self._body_log: RichLog | None = None

    def compose(self):
        yield Static(self.agent_id, classes="row-header")
        yield RichLog(wrap=False, highlight=False, markup=False, classes="row-body", id=f"body-{self.agent_id}")

    def on_mount(self) -> None:
        # Wire up the body log so .mark() can find it cheaply.
        try:
            self._body_log = self.query_one(f"#body-{self.agent_id}", RichLog)
        except Exception:
            self._body_log = None
        self._render()

    def _render(self) -> None:
        if self._body_log is None:
            return
        icon = _STATE_ICON.get(self.state, "○")
        wc = f"{self.wallclock_s:.1f}s" if self.wallclock_s is not None else ""
        text = f"{icon}  {wc:>6}"
        try:
            self._body_log.clear()
            self._body_log.write(text)
        except Exception:
            pass

    def mark(self, state: str, wallclock_s: float | None = None) -> None:
        self.state = state
        if wallclock_s is not None:
            self.wallclock_s = wallclock_s
        if self._body_log is None:
            # Not mounted yet; defer.
            self.call_after_refresh(self._render)
        else:
            self._render()


class ActivityPanel(Container):
    """Sidebar section. Owns one row per agent; updates in place."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("activity-panel")
        self._rows: dict[str, _AgentRow] = {}

    def compose(self):
        yield Static("Activity", classes="sidebar-heading")
        for agent_id in AGENT_IDS:
            row = _AgentRow(agent_id)
            self._rows[agent_id] = row
            yield row

    # --- public hooks called by ChatScreen -------------------------------- #
    def mark_running(self, agent_id: str) -> None:
        if agent_id in self._rows:
            self._rows[agent_id].mark("running")

    def mark_finished(self, agent_id: str, wallclock_s: float) -> None:
        if agent_id in self._rows:
            self._rows[agent_id].mark("done", wallclock_s=wallclock_s)

    def mark_failed(self, agent_id: str) -> None:
        if agent_id in self._rows:
            self._rows[agent_id].mark("failed")

    def reset(self) -> None:
        """Reset all rows to queued at the start of a new run."""
        for row in self._rows.values():
            row.mark("queued")
