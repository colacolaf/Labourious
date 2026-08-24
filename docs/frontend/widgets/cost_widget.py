"""
cost_widget.py — cumulative token + cost totals for the current run.

Three small lines: `in`, `out`, `est`. Updates per CostDelta event.

Uses a tiny RichLog body (instead of Static.update()) to avoid the
Static-with-str-renderable layout versioning issue in Textual 3.7.
"""

from __future__ import annotations

from textual.widgets import RichLog, Static


def _fmt(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}k"
    return str(n)


class CostWidget(Static):
    """Header label + a 3-line RichLog body."""

    def __init__(self, **kwargs) -> None:
        super().__init__("", markup=True, **kwargs)
        self.add_class("cost-widget")
        self._in = 0
        self._out = 0
        self._cost = 0.0

    def compose(self):
        yield Static("Cost", classes="sidebar-heading")
        rl = RichLog(wrap=False, highlight=False, markup=False, classes="cost-body", id="cost-body")
        rl.can_focus = False  # display-only; Tab should skip to the prompt
        yield rl

    def on_mount(self) -> None:
        self.render_text()

    def update_totals(self, in_tokens: int, out_tokens: int, cost_usd: float) -> None:
        self._in = in_tokens
        self._out = out_tokens
        self._cost = cost_usd
        self.render_text()

    def reset(self) -> None:
        self._in = 0
        self._out = 0
        self._cost = 0.0
        self.render_text()

    def render_text(self) -> None:
        try:
            log = self.query_one("#cost-body", RichLog)
            # Clear then re-write (RichLog doesn't have a stable clear-and-rewrite API in 3.7,
            # so we write a fresh line each time which works for the small 3-line display).
            log.clear()
            cost_str = f"${self._cost:.4f}" if self._cost < 1 else f"${self._cost:.2f}"
            log.write(f"in:  {_fmt(self._in):>7}")
            log.write(f"out: {_fmt(self._out):>7}")
            log.write(f"est: {cost_str:>7}")
        except Exception:
            # Body not yet mounted; defer to next refresh.
            self.call_after_refresh(self.render_text)
