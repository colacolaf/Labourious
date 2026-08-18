"""
chat.py — the default screen.

Layout (from SPEC.md §1): vertical container with:
    header (1 line)
    body  (Horizontal: Sidebar | Chat-scroll)
        Sidebar: ActivityPanel + CostWidget
        Chat: VerticalScroll of MessageBubbles, plus a banner above
    footer (1 line — status hint)
    input (1 line)

The screen owns:
    - the message-bubble log (a list of MessageBubble widgets)
    - the activity panel + cost widget (sidebar)
    - the prompt input bar
    - a one-line connection_banner above the chat scroll

Flow:
    1. User types a message, hits Enter.
    2. If `/command` → handle the command locally.
    3. Else: assume "analyze TICKER" → start f1 on the current ticker.
    4. The screen mounts a bubble for the user prompt, then enters Running state.
    5. As the runtime streams events, the screen mounts agent bubbles, updates
       the activity sidebar, updates the cost widget.
    6. On FlowFinished, the screen mounts the DiffPanel (if prior thesis exists)
       and the final-report bubble + its citation chip.
    7. On FlowFailed, it mounts an error bubble with the partial envelopes.
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Input, Static

# Make the sibling `runtime/` package importable when this screen is loaded
# via `python docs/frontend/app.py`. With docs/ on sys.path, both `frontend.X`
# and `runtime.X` resolve as packages.
_THIS = Path(__file__).resolve()
if str(_THIS.parents[2]) not in sys.path:
    sys.path.insert(0, str(_THIS.parents[2]))   # docs/

from frontend.widgets import (  # type: ignore
    ActivityPanel, CostWidget, CitationChip, ConnectionBanner,
    DiffPanel, MessageBubble,
)
from frontend.keys import COMMAND_PALETTE_PREFIX  # type: ignore
# Re-export the same event module the TUI uses (single source of truth: runtime/events.py)
from frontend.events import (  # type: ignore
    FlowStarted, FlowFinished, FlowFailed,
    AgentStarted, AgentFinished, AgentFailed, AgentChunk,
    ConnectorRequested, ConnectorCompleted, ConnectorFailed,
    ThesisPriorRead, ThesisWritten,
    CostDelta,
    is_known,
)
from runtime.runtime import run_flow_stream  # type: ignore
from runtime.mock_runtime import run_mock_flow_stream, mock_runtime_available  # type: ignore

from frontend.config_io import load_config, save_config, Config  # type: ignore


# --------------------------------------------------------------------------- #
# Welcome screen (idle state — first launch)
# --------------------------------------------------------------------------- #
WELCOME_TEMPLATE = """\
# Welcome

**{state_badge}** · model **·** `{model}` · depth **·** {depth} · compressed **·** {compressed} · paid-for **·** {paid_for}

Run the flagship flow on a ticker to begin. Try:

> `analyze NVDA`

Or set up first:
- `/model <provider/name>` — switch the default model
- `/depth STANDARD|DEEP` — set the depth for the next run
- `/paid-for <agents>` — toggle per-agent paid routing

Quick actions:
- `s` open Settings · `h` open History · `?` open Help
"""
QUICK_ACTION_HINT = (
    "(press `Tab` to focus the input — then type a prompt and press `Enter`)"
)



# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
TICKER_RE = re.compile(r"\b([A-Z]{1,5})\b")


def detect_ticker(text: str) -> str | None:
    """Best-effort: pull a 1-5 char uppercase token from the prompt."""
    m = TICKER_RE.search(text.upper())
    return m.group(1) if m else None


# --------------------------------------------------------------------------- #
# ChatScreen
# --------------------------------------------------------------------------- #
class ChatScreen(Screen):
    """The default screen. Mounts Header / Sidebar / Chat / Input / Footer."""

    BINDINGS = [
        Binding("ctrl+l", "clear_chat", "Clear chat"),
        Binding("ctrl+r", "rerun_last", "Re-run last"),
        Binding("enter",  "submit",     "Submit"),
    ]

    DEFAULT_CSS = ""  # the real theme lives in style.tcss

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Session state
        self.flow_id: str = "f1"
        self.model: str = "ollama/llama3.3:70b"
        self._initial_model: str | None = None  # set by App.get_default_screen before compose()
        self.paid_for: list[str] = []  # empty = fully free; ["final-report"] = hybrid
        self.depth: str = "STANDARD"
        self.compressed: bool = False
        self.ticker: str | None = None
        self.last_user_prompt: str = ""
        # In-memory transcript of bubble ids (so we can clear / re-run).
        self._bubble_index: dict[str, MessageBubble] = {}
        # Per-agent model overrides — populated from Config on init; refreshed
        # when the Settings modal saves (see reload_config_from_disk below).
        self.per_agent_model: dict[str, str] = {}
        # Streaming mode — when True, each adapter's `.stream()` feeds the
        # bubble with one AgentChunk per text delta (incremental). When
        # False, the runtime emits one AgentChunk per agent with the full
        # body (cheaper, but no perceived typing effect). Default ON for
        # the real runtime; the mock runtime ignores this flag.
        self.stream_chunks: bool = True
        # Typewriter delay in ms between AgentChunk dispatches. 0 = no delay.
        # Configurable via Settings → streaming → typewriter_ms.
        self.stream_typewriter_ms: int = 0
        # Last ThesisWritten event captured (used to populate the
        # citation chip with real data, not just a count).        self._last_thesis: dict | None = None

    # --------------------------------------------------------------- compose
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="sidebar"):
                yield ActivityPanel(id="activity")
                yield CostWidget(id="cost")
                yield Static("Thesis register", classes="sidebar-heading")
                yield Static("(empty)", id="thesis-snapshot", classes="sidebar-meta")
            with Vertical(id="chat-pane"):
                yield ConnectionBanner(id="banner")
                yield VerticalScroll(id="chat-log")
        yield Input(
            placeholder="> analyze NVDA at $890  (try `/help` for commands)",
            id="prompt",
        )
        # StatusStrip replaces the default `Footer` because:
        # - we want the `? help` right-corner tag as a consistent affordance
        # - we want screen-aware key hints that swap when a modal pushes/pops
        from frontend.widgets.status_strip import StatusStrip   # type: ignore
        yield StatusStrip()

    # ----------------------------------------------------------------- on_mount
    def on_mount(self) -> None:
        # Forward initial model if set by the App at composition time.
        if self._initial_model:
            self.model = self._initial_model
        # Read live config FIRST so welcome renders with up-to-date values.
        self.reload_config_from_disk()
        # Show welcome card on first launch.
        self._show_welcome()
        self._update_footer_hint()
        # Refresh the screen-aware bottom strip to show chat keys.
        from frontend.widgets.status_strip import StatusStrip as _SS
        try:
            self.query_one(_SS).update_for(self)
        except Exception:
            pass

    # ------------------------------------------------------------- public hooks (called by parent App)
    def set_status_footer(self, msg: str) -> None:
        """Publish a transient status into the StatusStrip (the universal
        bottom strip). Used by _update_footer_hint to display flow status
        ("✓ run complete", "⏳ running f1", "! flow failed")."""
        try:
            from frontend.widgets.status_strip import StatusStrip
            self.query_one(StatusStrip).set_status(msg)
        except Exception:
            pass

    def set_model(self, model: str) -> None:
        self.model = model
        # Persist to the on-disk config so Settings honors it too.
        try:
            cfg = load_config()
            cfg.default_model = model
            save_config(cfg)
        except Exception:
            pass
        self._update_footer_hint()

    def set_paid_for(self, agents: list[str]) -> None:
        self.paid_for = list(agents)
        # Persist to on-disk config (`hybrid_paid_for`) for the Settings UI.
        try:
            cfg = load_config()
            cfg.hybrid_paid_for = list(agents)
            save_config(cfg)
        except Exception:
            pass
        self._update_footer_hint()

    def set_depth(self, depth: str) -> None:
        if depth not in ("SCAN", "STANDARD", "DEEP"):
            return
        self.depth = depth
        try:
            cfg = load_config()
            cfg.defaults_depth = depth
            save_config(cfg)
        except Exception:
            pass
        self._update_footer_hint()

    def set_compressed(self, on: bool) -> None:
        self.compressed = bool(on)
        try:
            cfg = load_config()
            cfg.defaults_compressed = bool(on)
            save_config(cfg)
        except Exception:
            pass
        self._update_footer_hint()

    def reload_config_from_disk(self) -> None:
        """Re-read ~/.labourious/config.json into this ChatScreen's session
        state. Called on mount and after the Settings modal pops."""
        try:
            cfg: Config = load_config()
        except Exception:
            return
        # Don't clobber a higher-precedence /model command from the input
        # palette; only update from disk if the user hasn't overridden
        # recently. We treat env var LABOURIOUS_MODEL as the only override
        # that wins on top of disk.
        import os
        if not os.environ.get("LABOURIOUS_MODEL"):
            if cfg.default_model:
                self.model = cfg.default_model
        self.depth = cfg.defaults_depth or "STANDARD"
        self.compressed = bool(cfg.defaults_compressed)
        self.paid_for = list(cfg.hybrid_paid_for or [])
        # Per-agent overrides from disk (used by the runtime adapter).
        self.per_agent_model = dict(cfg.per_agent_model or {})
        # Streaming UX — read from disk so Settings saves propagate here.
        self.stream_chunks = bool(getattr(cfg, "stream_chunks", True))
        self.stream_typewriter_ms = int(
            getattr(cfg, "stream_typewriter_ms", 0) or 0)
        self._update_footer_hint()

    def set_flow(self, flow_id: str) -> None:
        self.flow_id = flow_id
        self._update_footer_hint()

    # ------------------------------------------------------------- chat actions
    async def action_submit(self) -> None:
        text = self.query_one("#prompt", Input).value.strip()
        if not text:
            return

        # Intercept command palette first.
        if text.startswith("/"):
            await self._handle_command(text[1:].strip())
            self.query_one("#prompt", Input).value = ""
            return

        # Cache last prompt so Ctrl+R can replay it.
        self.last_user_prompt = text

        # Mount a user bubble.
        user_bubble = MessageBubble(role="user", agent_id="user")
        await self.query_one("#chat-log", VerticalScroll).mount(user_bubble)
        user_bubble.append_delta(text)

        # Ticker detection: prefer explicit mentions, else fall back to /ticker.
        ticker = detect_ticker(text) or self.ticker
        if ticker is None:
            self._set_banner_warning("No ticker detected. Try `/ticker NVDA` then re-run.")
            return

        self.ticker = ticker
        await self._run_flow(self.flow_id, ticker, text)

        # Reset input.
        self.query_one("#prompt", Input).value = ""

    async def action_clear_chat(self) -> None:
        await self.query_one("#chat-log", VerticalScroll).remove_children()
        self._bubble_index.clear()
        self._last_thesis = None
        self.query_one(ActivityPanel).reset()
        self.query_one(CostWidget).reset()
        self._set_banner_ok()
        self._show_welcome()

    async def action_rerun_last(self) -> None:
        if self.last_user_prompt:
            self.query_one("#prompt", Input).value = self.last_user_prompt
            await self.action_submit()

    # --------------------------------------------------------- command palette
    async def _handle_command(self, body: str) -> None:
        parts = body.split(maxsplit=1)
        cmd, arg = (parts[0].lower(), parts[1].strip() if len(parts) > 1 else "")
        # Quick help / quit / clear
        if cmd == "help":
            self._show_welcome(force=True)
            return
        if cmd in ("quit", "exit"):
            self.app.exit()
            return
        if cmd in ("clear", "reset"):
            await self.action_clear_chat()
            return
        if cmd == "settings":
            # App-level action (Textual action names from keys.py).
            self.app.action_open_settings()
            return
        if cmd == "history":
            self.app.action_open_history()
            return
        if cmd == "flow":
            self.set_flow(arg)
            return
        if cmd == "ticker":
            self.ticker = arg.upper()
            return
        if cmd == "model":
            self.set_model(arg)
            return
        if cmd == "paid-for":
            self.set_paid_for([a.strip() for a in arg.split(",") if a.strip()])
            return
        if cmd == "depth":
            if arg.upper() in ("SCAN", "STANDARD", "DEEP"):
                self.set_depth(arg.upper())
            return
        if cmd == "compressed":
            self.set_compressed(not self.compressed)
            return
        # Unrecognised — surface in a bubble.
        bubble = MessageBubble(role="agent", agent_id="devils-advocate")
        await self.query_one("#chat-log", VerticalScroll).mount(bubble)
        bubble.append_delta(f"_Unknown command: `/{cmd}` — press **?** for help._")

    # --------------------------------------------------------------- run flow
    async def _run_flow(self, flow_id: str, ticker: str, user_query: str) -> None:
        """Mount bubbles reactively as events stream from run_flow_stream."""
        # Pre-allocate one bubble per agent + the orchestrator. Activity panel
        # is reset by App-level state-machine logic (R1 polish).
        self.query_one(ActivityPanel).reset()
        self.query_one(CostWidget).reset()
        self._bubble_index.clear()
        self._last_thesis = None

        inputs = {
            "ticker": ticker,
            "depth": self.depth,
            "compressed": self.compressed,
        }

        def _on_event_sync():
            """Inner generator. Consumes events in a thread; schedules UI updates."""
            # Pick the runtime: mock for pilots/demos, real for production.
            src = run_mock_flow_stream if mock_runtime_available() else run_flow_stream
            # stream_chunks=True routes through each adapter's .stream() and
            # emits one AgentChunk per text delta — the TUI bubbles update
            # incrementally instead of waiting for the full body. Set False
            # only if the user prefers the cheaper bundled-emission path.
            for event in src(flow_id, inputs, self.model, self.paid_for,
                             per_agent_model=self.per_agent_model or None,
                             stream_chunks=self.stream_chunks):
                if not is_known(event):
                    continue
                # Marshal back to the UI thread.
                self.app.call_from_thread(self._apply_event, event)

        # Run the blocking sync iterator in a worker thread.
        await asyncio.to_thread(_on_event_sync)

    def _apply_event(self, event) -> None:
        """UI-thread handler — mounts / updates widgets for each event."""
        log = self.query_one("#chat-log", VerticalScroll)
        activity = self.query_one(ActivityPanel)
        cost = self.query_one(CostWidget)
        banner = self.query_one(ConnectionBanner)

        if isinstance(event, FlowStarted):
            banner.set_ok()
            activity.reset()
            cost.reset()
            thesis_snap = self.query_one("#thesis-snapshot")
            n_prior = len(event.thesis_register_snapshot)
            thesis_snap.update(
                f"{n_prior} prior run{'s' if n_prior != 1 else ''}" if n_prior else "(empty)"
            )

        elif isinstance(event, ThesisPriorRead):
            # (Already shown in thesis snapshot at FlowStarted.)
            pass

        elif isinstance(event, AgentStarted):
            bubble = MessageBubble(role="agent", agent_id=event.agent_id)
            log.mount(bubble)
            self._bubble_index[event.agent_id] = bubble
            bubble.mark_started(model=event.model)
            activity.mark_running(event.agent_id)

        elif isinstance(event, AgentChunk):
            bubble = self._bubble_index.get(event.agent_id)
            if bubble is not None:
                # Apply user-configured typewriter delay (ms) before the
                # delta lands, so the bubble grows at a human-readable pace
                # even on providers whose streamed throughput exceeds reading
                # speed (Groq, Cerebras, etc). 0 = instant.
                if self.stream_typewriter_ms > 0:
                    import time as _time
                    _time.sleep(self.stream_typewriter_ms / 1000.0)
                bubble.append_delta(event.delta)

        elif isinstance(event, ConnectorRequested):
            # Acknowledged but no UI yet — the strip's chips light up on
            # the matching ConnectorCompleted / ConnectorFailed.
            pass

        elif isinstance(event, ConnectorCompleted):
            # Route the strip entry to the most recent agent bubble. The runtime
            # event currently doesn't carry `requested_by_agent` — when it does,
            # we can route precisely. For now the fallback gives every tool call
            # the bubble that last started, so the user sees what fired.
            bubble = self._last_bubble() or self._bubble_index.get("final-report")
            if bubble is not None:
                bubble.record_connector_fired(
                    tool=event.tool,
                    status=event.status,
                    as_of=event.as_of,
                    note=event.note,
                    data_summary=event.data_summary,
                )
            # Refresh the footer counter (cumulative across bubbles).
            self._update_footer_hint()

        elif isinstance(event, ConnectorFailed):
            bubble = self._last_bubble() or self._bubble_index.get("final-report")
            if bubble is not None:
                bubble.record_connector_failed(
                    tool=event.tool,
                    error=event.error,
                )
            self._update_footer_hint()

        elif isinstance(event, AgentFinished):
            bubble = self._bubble_index.get(event.agent_id)
            if bubble is not None:
                envelope = event.envelope or {}
                citations = len(envelope.get("citations", []) or [])
                confidence = envelope.get("confidence", "MEDIUM")
                bubble.mark_finished(
                    wallclock_s=event.wallclock_s,
                    confidence=confidence,
                    citations=citations,
                )
            activity.mark_finished(event.agent_id, wallclock_s=event.wallclock_s)

        elif isinstance(event, CostDelta):
            cost.update_totals(event.cumulative_in, event.cumulative_out, event.cumulative_cost)

        elif isinstance(event, ThesisWritten):
            snap = self.query_one("#thesis-snapshot")
            snap.update(f"v{event.version} just written · {event.conviction}/5")
            # Stash the full event so FlowFinished can wire it into the chip.
            self._last_thesis = {
                "thesis_id":   event.thesis_id,
                "version":     event.version,
                "conviction":  event.conviction,
                "evidence_urls": list(event.evidence_urls or []),
            }

        elif isinstance(event, FlowFinished):
            # Mount a citation chip on the final-report bubble if citations > 0.
            fr = self._bubble_index.get("final-report")
            thesis = self._last_thesis or {}
            chips_to_attach = []
            if fr is not None and (thesis.get("evidence_urls") or fr._citation_count):
                chip = CitationChip(
                    citations=thesis.get("evidence_urls", []),
                    agent_id="final-report",
                    thesis_id=thesis.get("thesis_id"),
                    version=thesis.get("version"),
                    timestamp=None,
                    classes="final-chip",
                )
                chips_to_attach.append(chip)
            # Also let other agents (senior-analyst, devils-advocate, ...)
            # mount their own chips if their envelope has citations. The
            # runtime currently only emits citations_used on the thesis-
            # wide envelope, but we forward the same list to the matching
            # bubble if it has a non-zero count.
            for agent_id, bubble in self._bubble_index.items():
                if agent_id == "final-report":
                    continue
                if bubble._citation_count and thesis.get("evidence_urls"):
                    chips_to_attach.append(CitationChip(
                        citations=thesis["evidence_urls"],
                        agent_id=agent_id,
                        thesis_id=thesis.get("thesis_id"),
                        version=thesis.get("version"),
                        timestamp=None,
                        classes="agent-chip",
                    ))
            for chip in chips_to_attach:
                log.mount(chip)
            # Mount a DiffPanel above the final-report bubble if prior existed.
            if event.final_envelope:
                try:
                    prior = event.final_envelope.get("_prior_thesis", [])
                except Exception:
                    prior = []
                diff = DiffPanel.maybe_build(prior, {
                    "thesis_text": event.final_envelope.get("thesis_text", ""),
                    "conviction":  event.final_envelope.get("conviction", "?"),
                })
                if diff is not None:
                    log.mount(diff)
            self._update_footer_hint(suffix=" · run complete")


        elif isinstance(event, FlowFailed):
            banner.set_error(f"Flow failed at {event.failed_agent_id or '?'}: {event.reason}")
            # Show partial envelopes in an error bubble.
            if event.partial_envelopes:
                err_bubble = MessageBubble(role="agent", agent_id="devils-advocate")
                log.mount(err_bubble)
                err_bubble.append_delta(
                    f"_Flow failed at **{event.failed_agent_id}**._\n\n"
                    f"Partial envelopes:\n```json\n"
                    f"{json.dumps(event.partial_envelopes, indent=2)[:1200]}\n```"
                )
                err_bubble.mark_failed(event.reason)

    # ---------------------------------------------------------- chip press
    def on_citation_chip_pressed(self, message) -> None:
        """User pressed Enter on (or clicked) a CitationChip.

        We resolve the chip by id (the chip carries the citation list and
        metadata), grab the data, and push a ``CitationModalScreen`` on
        top of this chat screen.
        """
        try:
            chip = self.query_one(f"#{message.chip_id}", CitationChip)
        except Exception:
            return
        if not chip.citations:
            try:
                self._set_banner_warning("This chip has no citation list attached.")
            except Exception:
                pass
            return
        # Tiny timestamp so the modal knows when the user opened it
        # (useful for future "opened Xs ago" affordances if we add them).
        try:
            from datetime import datetime
            ts = datetime.now().strftime("%H:%M:%S")
        except Exception:
            ts = None
        from frontend.screens import CitationModalScreen
        modal = CitationModalScreen(
            agent_id=chip.agent_id or "(unknown)",
            citations=list(chip.citations),
            thesis_id=chip.thesis_id,
            version=chip.version,
            timestamp=ts,
        )  # The screen sets its own id in __init__ (idempotent).
        self.app.push_screen(modal)

    # ---------------------------------------------------------- internal helpers
    def _show_welcome(self, force: bool = False) -> None:
        log = self.query_one("#chat-log", VerticalScroll)
        # Only show on first mount unless forced.
        if not force and log.children:
            return
        bubble = MessageBubble(role="agent", agent_id="orchestrator")
        log.mount(bubble)
        # Render the welcome using live session state + mock hint, so the
        # user sees their actual model + flags without having to open
        # settings to discover what's configured.
        import os as _os
        mock_on = bool(_os.environ.get("LABOURIOUS_MOCK"))
        state_badge = "MOCK runtime — no LLM calls" if mock_on else "Ready"
        paid = ",".join(self.paid_for) if self.paid_for else "none"
        text = WELCOME_TEMPLATE.format(
            state_badge=state_badge,
            model=self.model,
            depth=self.depth,
            compressed="true" if self.compressed else "false",
            paid_for=paid,
        )
        text += "\n" + QUICK_ACTION_HINT
        bubble.append_delta(text)

    def _set_banner_warning(self, msg: str) -> None:
        self.query_one(ConnectionBanner).set_warning(msg)

    def _set_banner_ok(self) -> None:
        self.query_one(ConnectionBanner).set_ok()

    def _update_footer_hint(self, suffix: str = "") -> None:
        paid = ",".join(self.paid_for) if self.paid_for else "none"
        connector_prefix = self._connector_footer_segment()
        base = f"{connector_prefix}{self.flow_id} · {self.model} · paid-for: {paid} · depth: {self.depth}"
        self.set_status_footer(base + suffix)

    def _connector_footer_segment(self) -> str:
        """Roll up the connector state across every bubble that's mounted and
        prepend a compact '3/9 active (1 stale)' counter into the footer.

        Empty string when nothing has fired yet — keeps the cold-start footer clean.
        """
        from frontend.widgets.connector_strip import (
            ConnectorStripState,
            connectors_footer_segment,
        )
        agg = ConnectorStripState()
        # Walk every mounted bubble; merge its chip map.
        for bubble in (self._bubble_index or {}).values():
            try:
                st = bubble.connector_state()
            except Exception:
                continue
            agg.chips.update(st.chips)
        if not agg.chips:
            return ""  # cold start
        return connectors_footer_segment(agg) + "  \u00b7  "

    def _last_bubble(self):
        """The bubble that was most recently started — where connector
        firings land while agent routing is undetermined."""
        if not getattr(self, "_bubble_index", None):
            return None
        try:
            return list(self._bubble_index.values())[-1]
        except Exception:
            return None
