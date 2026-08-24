"""
message_bubble.py — one chat bubble ("▌  user" or "▌  <agent_id>").

A bubble is a *Container* with:
  - a header `Static` (carries border_title, agent_id, timing, confidence)
  - a `RichLog` body (the streaming markdown content)

Uses `RichLog` for the body (instead of `Static.update()` with strings)
because Textual 3.7.x's Static → string renderable pipeline has known
layout-versioning issues when you mutate str content in-place. RichLog is the
bulletproof widget for chat-style streaming text.

States:
    waiting    -> placeholder body ("▌ waiting for response...")
    streaming  -> body being appended (AgentChunk events)
    finished   -> header gets wallclock/confidence; chip line appended
    failed     -> body shows error + retry hint
"""

from __future__ import annotations

from datetime import datetime

from textual.containers import Vertical
from textual.widgets import RichLog, Static


def _now_hms() -> str:
    return datetime.now().strftime("%H:%M:%S")


class MessageBubble(Vertical):
    """Bubble: header (border-title on a static) + RichLog body."""

    CONFIDENCE_CLASS = {
        "HIGH":           "conf-high",
        "MODERATE_HIGH":  "conf-moderate-high",
        "MODERATE":       "conf-moderate",
        "MODERATE_LOW":   "conf-moderate-low",
        "LOW":           "conf-low",
        "ABSTAIN":       "conf-abstain",
    }

    AGENT_STATE_ICON = {
        "waiting":   "○",
        "started":   "◐",
        "finished":  "✓",
        "failed":    "✗",
    }

    AGENT_ACCENT_CLASS = {
        "orchestrator":       "accent-o",
        "senior-analyst":     "accent-s",
        "forensic-accounting": "accent-f",
        "devils-advocate":    "accent-d",
        "final-report":       "accent-r",
        "user":               "accent-user",
    }

    def __init__(
        self,
        role: str = "agent",       # "user" or "agent"
        agent_id: str = "agent",
        **kwargs,
    ) -> None:
        accent = self.AGENT_ACCENT_CLASS.get(agent_id, "accent-default")
        super().__init__(**kwargs)
        self.role = role
        self.agent_id = agent_id
        self.state = "waiting"
        self._wallclock_s: float | None = None
        self._confidence: str | None = None
        self._citation_count: int = 0
        self._model: str | None = None
        # Classes
        self.add_class("bubble")
        self.add_class(f"bubble-{role}")
        self.add_class(accent)

    def compose(self):
        # Header is a Static carrying the border_title (role/agent_id + timing + confidence).
        yield Static(self._title_text(), classes="bubble-header")
        # Body is a RichLog. Wrap=True for visual flow; highlight=False for plain text rendering speed.
        rl = RichLog(wrap=True, highlight=False, markup=False, classes="bubble-body")
        rl.can_focus = False  # Tab skips display-only bubbles, reaches prompt directly
        yield rl
        # Connector strip (third child) — the '▾ via: A · B · C' line that
        # shows which data sources this agent pulled. Defaults to '(none fired)'
        # and gets updated by chat.py on ConnectorCompleted / ConnectorFailed.
        from frontend.widgets.connector_strip import BubbleConnectorStrip  # local import
        yield BubbleConnectorStrip(classes="bubble-connectors")

    # -- private helpers ------------------------------------------------- #
    def _title_text(self) -> str:
        header = self.agent_id if self.role == "agent" else "user"
        ts = _now_hms()
        extras: list[str] = []
        if self._wallclock_s is not None:
            extras.append(f"{self._wallclock_s:.1f}s")
        if self._confidence is not None:
            extras.append(self._confidence)
        # NOTE: model is shown in ActivityPanel sidebar, not in the line
        # bubble header — the line header is the audible "what just happened"
        # (agent + timestamp + status) and should never overflow on narrow
        # terminals. If you also need the model in the bubble, expose it as
        # an expander key rather than inline.
        suffix = ("  ·  " + "  ·  ".join(extras)) if extras else ""
        return f"{self.AGENT_STATE_ICON[self.state]}  {header}  {ts}{suffix}"

    def _refresh_title(self) -> None:
        # The header Static is the first child.
        self.query_one(".bubble-header", Static).update(self._title_text())

    def _body(self) -> RichLog:
        return self.query_one(".bubble-body", RichLog)

    # -- lifecycle hooks called by chat.py -------------------------------- #
    def mark_started(self, model: str | None = None) -> None:
        self.state = "started"
        self._model = model
        # If the bubble's compose() hasn't fully mounted yet (race condition
        # when an AgentStarted event streams in faster than the prior mount),
        # defer the header refresh until after the next refresh cycle.
        try:
            self._refresh_title()
        except Exception:
            # bubble-header Static isn't there yet; defer.
            self.call_after_refresh(self._refresh_title)

    def _refresh_title_late(self) -> None:
        try:
            self._refresh_title()
        except Exception:
            pass

    def append_delta(self, delta: str) -> None:
        """Append text to the body. Tolerates compose() not having mounted yet
        by buffering and flushing once the body is available."""
        self.state = "started"
        try:
            self._body().write(delta)
        except Exception:
            # Bubble isn't composed yet. Schedule a flush after refresh.
            self._pending_deltas.append(delta)
            self.call_after_refresh(self._flush_pending)

    def _flush_pending(self) -> None:
        if not getattr(self, "_pending_deltas", []):
            return
        try:
            body = self._body()
            for d in self._pending_deltas:
                body.write(d)
            self._pending_deltas.clear()
        except Exception:
            # Still not ready; try again next cycle.
            self.call_after_refresh(self._flush_pending)

    @property
    def _pending_deltas(self) -> list[str]:
        if not hasattr(self, "_pending_buf"):
            self._pending_buf = []
        return self._pending_buf

    def mark_finished(
        self,
        wallclock_s: float,
        confidence: str | None = None,
        citations: int = 0,
    ) -> None:
        self.state = "finished"
        self._wallclock_s = wallclock_s
        self._confidence = confidence or "MEDIUM"
        self._citation_count = citations
        chip_text = f"\n[ {citations} citation{'s' if citations != 1 else ''} ]" if citations else "\n(no citations)"
        try:
            self._body().write(chip_text)
        except Exception:
            self.call_after_refresh(self._flush_finished, chip_text)
        try:
            self._refresh_title()
        except Exception:
            self.call_after_refresh(self._refresh_title)
        self._apply_confidence_class()

    def _flush_finished(self, chip_text: str) -> None:
        try:
            self._body().write(chip_text)
        except Exception:
            pass

    def mark_failed(self, error: str) -> None:
        self.state = "failed"
        try:
            self._body().write(f"\n⚠ {error}\n\nRe-run with Ctrl+R.")
        except Exception:
            self.call_after_refresh(self._flush_failed, error)
        try:
            self._refresh_title()
        except Exception:
            # bubble-header Static not yet mounted; defer.
            self.call_after_refresh(self._refresh_title)
        self.add_class("conf-low")

    def _flush_failed(self, error: str) -> None:
        try:
            self._body().write(f"\n⚠ {error}\n\nRe-run with Ctrl+R.")
        except Exception:
            pass

    # -- internals -------------------------------------------------------- #
    def _apply_confidence_class(self) -> None:
        for cls in self.CONFIDENCE_CLASS.values():
            self.remove_class(cls)
        if self._confidence is not None:
            cls = self.CONFIDENCE_CLASS.get(self._confidence)
            if cls is not None:
                self.add_class(cls)

    # -- connector strip -------------------------------------------------- #
    def _strip(self):
        """Resolve the embedded BubbleConnectorStrip widget (lazy import safe)."""
        try:
            from frontend.widgets.connector_strip import BubbleConnectorStrip  # type: ignore
            return self.query_one(BubbleConnectorStrip)
        except Exception:
            return None

    def record_connector_fired(self, **kw) -> None:
        """Forward a success-side ConnectorCompleted event into the strip."""
        strip = self._strip()
        if strip is None:
            return
        strip.record_fired(**kw)

    def record_connector_failed(self, **kw) -> None:
        """Forward a ConnectorFailed event into the strip."""
        strip = self._strip()
        if strip is None:
            return
        strip.record_failed(**kw)

    def connector_state(self):
        """Read the current ConnectorStripState; used by chat.py to roll up footer counts.

        Returns an empty state if the strip widget isn't mounted yet (race condition)."""
        from frontend.widgets.connector_strip import ConnectorStripState  # type: ignore
        strip = self._strip()
        if strip is None:
            return ConnectorStripState()
        # The strip widget owns its state privately; expose a snapshot copy.
        return ConnectorStripState(chips=dict(strip._state.chips))
