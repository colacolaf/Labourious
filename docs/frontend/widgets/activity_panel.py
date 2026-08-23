"""
activity_panel.py — the sidebar's per-agent status list.

One row per agent. Each row shows:
  - state icon (○ queued / ◐ running / ● done / ✗ failed / – skipped)
  - wallclock (elapsed while running, final when done)
  - cost-so-far (from CostDelta events, updated live)
  - model name (from AgentStarted, e.g. "claude-sonnet-4-5")

Below the rows, a summary footer line shows:
  - ETA: average wallclock of completed agents × remaining count
  - Cumulative cost (from CostDelta.cumulative_cost)

The chat screen calls:
  .mark_running(agent_id, model)          — on AgentStarted
  .mark_finished(agent_id, wallclock_s, cost, tokens_in, tokens_out) — on AgentFinished
  .mark_failed(agent_id)                  — on AgentFailed
  .update_cost(agent_id, cost, cumulative_cost) — on CostDelta
  .reset()                                — before a new flow starts
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


def _fmt_tokens(n: int) -> str:
    """Compact token display: 1234 → \"1.2k\", 1000000 → \"1.0M\"."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


def _fmt_cost(cost: float) -> str:
    """Compact cost display. < $0.01 → \"$0.000\", else 2-4 decimal places."""
    if cost == 0.0:
        return "$0"
    if cost < 0.01:
        return f"${cost:.4f}" if cost >= 0.0001 else "$0"
    if cost < 1:
        return f"${cost:.3f}"
    return f"${cost:.2f}"


def _short_model(model: str) -> str:
    """Compress 'anthropic/claude-sonnet-4-5' → 'sonnet-4-5'."""
    if "/" in model:
        _, _, slug = model.partition("/")
        # Drop provider prefix, keep model-identifying part
        parts = slug.split("-")
        if parts[0] in ("claude", "gpt", "gemini", "command", "llama", "qwen", "deepseek", "mixtral", "gemma", "phi"):
            return "-".join(parts[1:]) if len(parts) > 1 else slug
        return slug
    return model


class _AgentRow(Vertical):
    """Single row: header (agent_id) + one-line RichLog body.

    Body format: ``◐  3.2s  $0.012  sonnet-4-5``
    """

    def __init__(self, agent_id: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.agent_id = agent_id
        self.state = "queued"
        self.wallclock_s: float | None = None
        self.cost_usd: float = 0.0
        self.model: str = "—"
        self.tokens_in: int = 0
        self.tokens_out: int = 0
        self.add_class("activity-row")
        self.add_class(f"row-{agent_id}")
        self._body_log: RichLog | None = None

    def compose(self):
        yield Static(self.agent_id, classes="row-header")
        yield RichLog(wrap=False, highlight=False, markup=False,
                      classes="row-body", id=f"body-{self.agent_id}")

    def on_mount(self) -> None:
        try:
            self._body_log = self.query_one(f"#body-{self.agent_id}", RichLog)
        except Exception:
            self._body_log = None
        self._update_row()

    # NOTE: named `_update_row`, NOT `_render` — overriding Textual's
    # internal Widget._render() (which must return a Rich renderable)
    # with a None-returning method crashes the paint pipeline.
    def _update_row(self) -> None:
        if self._body_log is None:
            return
        icon = _STATE_ICON.get(self.state, "○")
        wc = f"{self.wallclock_s:.1f}s" if self.wallclock_s is not None else "  —  "
        cost_str = _fmt_cost(self.cost_usd)
        model_short = _short_model(self.model)

        if self.state == "queued":
            text = f"{icon}  {wc:>5}  {cost_str:>8}  {model_short}"
        elif self.state == "running":
            text = f"{icon}  {wc:>5}  {cost_str:>8}  {model_short}"
        elif self.state == "done":
            tok = f"{_fmt_tokens(self.tokens_in)}→{_fmt_tokens(self.tokens_out)}"
            text = f"{icon}  {wc:>5}  {cost_str:>8}  {model_short}  {tok}"
        else:
            text = f"{icon}  {wc:>5}  {cost_str:>8}  {model_short}"

        try:
            self._body_log.clear()
            self._body_log.write(text)
        except Exception:
            pass

    def mark_running(self, model: str = "—") -> None:
        self.state = "running"
        self.model = model
        self.wallclock_s = 0.0
        self.cost_usd = 0.0
        self.tokens_in = 0
        self.tokens_out = 0
        if self._body_log is None:
            self.call_after_refresh(self._update_row)
        else:
            self._update_row()

    def mark_finished(self, wallclock_s: float, cost_usd: float = 0.0,
                      tokens_in: int = 0, tokens_out: int = 0) -> None:
        self.state = "done"
        self.wallclock_s = wallclock_s
        self.cost_usd = cost_usd
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        if self._body_log is None:
            self.call_after_refresh(self._update_row)
        else:
            self._update_row()

    def mark_failed(self) -> None:
        self.state = "failed"
        if self._body_log is None:
            self.call_after_refresh(self._update_row)
        else:
            self._update_row()

    def update_cost(self, cost_usd: float) -> None:
        """Update live cost while the agent is running (from CostDelta)."""
        self.cost_usd = cost_usd
        if self._body_log is not None:
            self._update_row()


class ActivityPanel(Container):
    """Sidebar section: per-agent rows + summary footer with ETA."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.add_class("activity-panel")
        self._rows: dict[str, _AgentRow] = {}
        # ETA tracking
        self._completed_wallclocks: list[float] = []
        self._remaining_count: int = len(AGENT_IDS)
        self._cumulative_cost: float = 0.0
        self._summary_log: RichLog | None = None

    def compose(self):
        yield Static("Activity", classes="sidebar-heading")
        for agent_id in AGENT_IDS:
            row = _AgentRow(agent_id)
            self._rows[agent_id] = row
            yield row
        yield RichLog(wrap=False, highlight=False, markup=False,
                      classes="activity-summary", id="activity-summary")

    def on_mount(self) -> None:
        try:
            self._summary_log = self.query_one("#activity-summary", RichLog)
        except Exception:
            self._summary_log = None
        self._render_summary()

    # --- public hooks called by ChatScreen -------------------------------- #

    def mark_running(self, agent_id: str, model: str = "—") -> None:
        """Agent started — mark it running and update ETA estimate."""
        if agent_id in self._rows:
            self._rows[agent_id].mark_running(model=model)
        self._remaining_count = max(0, self._remaining_count - 1)
        self._render_summary()

    def mark_finished(self, agent_id: str, wallclock_s: float,
                      cost_usd: float = 0.0,
                      tokens_in: int = 0, tokens_out: int = 0) -> None:
        """Agent finished — record wallclock for ETA averaging."""
        if agent_id in self._rows:
            self._rows[agent_id].mark_finished(
                wallclock_s, cost_usd=cost_usd,
                tokens_in=tokens_in, tokens_out=tokens_out)
        if wallclock_s > 0:
            self._completed_wallclocks.append(wallclock_s)
        self._render_summary()

    def mark_failed(self, agent_id: str) -> None:
        if agent_id in self._rows:
            self._rows[agent_id].mark_failed()
        self._remaining_count = max(0, self._remaining_count - 1)
        self._render_summary()

    def update_cost(self, agent_id: str, cost_usd: float,
                    cumulative_cost: float) -> None:
        """Update live per-agent and cumulative cost."""
        if agent_id in self._rows:
            self._rows[agent_id].update_cost(cost_usd)
        self._cumulative_cost = cumulative_cost
        self._render_summary()

    def reset(self) -> None:
        """Reset all rows to queued at the start of a new run."""
        for row in self._rows.values():
            row.state = "queued"
            row.wallclock_s = None
            row.cost_usd = 0.0
            row.model = "—"
            row.tokens_in = 0
            row.tokens_out = 0
            if row._body_log is not None:
                row._update_row()
        self._completed_wallclocks.clear()
        self._remaining_count = len(AGENT_IDS)
        self._cumulative_cost = 0.0
        self._render_summary()

    # --- internal --------------------------------------------------------- #

    def _render_summary(self) -> None:
        if self._summary_log is None:
            return
        total = len(AGENT_IDS)
        done = len(self._completed_wallclocks)
        remaining = max(0, total - done)

        # ETA: average wallclock of completed × remaining
        eta_str = "—"
        if self._completed_wallclocks and remaining > 0:
            avg_s = sum(self._completed_wallclocks) / len(self._completed_wallclocks)
            eta_s = avg_s * remaining
            if eta_s < 60:
                eta_str = f"~{eta_s:.0f}s"
            else:
                m = int(eta_s // 60)
                s = int(eta_s % 60)
                eta_str = f"~{m}m{s:02d}s"

        cost_str = _fmt_cost(self._cumulative_cost)

        try:
            self._summary_log.clear()
            self._summary_log.write(
                f"  {done}/{total} done  ·  ETA {eta_str}  ·  Σ {cost_str}"
            )
        except Exception:
            pass