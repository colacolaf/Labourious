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
    DiffPanel, MessageBubble, TickerShortcuts,
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

Pick a ticker below to start the flagship flow, or type your own prompt:

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
        # Ticker shortcut chips — only useful when the chat-log is empty;
        # the screen hides them as soon as a flow starts. See
        # `_sync_shortcuts_visibility`.
        yield TickerShortcuts(id="ticker-shortcuts")
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
        # [ux-1] Welcome wizard: on first run with no providers configured,
        # push the guided onboarding modal. After completion (or skip),
        # the chat reloads the fresh config.
        cfg = load_config()
        if not cfg.providers:
            from frontend.screens.welcome_wizard import WelcomeWizardScreen
            self.app.push_screen(WelcomeWizardScreen(), callback=self._on_wizard_done)

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

    def set_stream(self, value: str) -> None:
        """Handle /stream on|off|<ms> — toggle or set the typewriter delay.

        Accepts:
          on   → stream_chunks=True, typewriter_ms=0 (instant)
          off  → stream_chunks=False (bundled full-body emission)
          <N>  → stream_chunks=True, typewriter_ms=N (human-readable pace)
        """
        arg = value.lower().strip() if value else "on"
        if arg == "on":
            self.stream_chunks = True
            self.stream_typewriter_ms = 0
        elif arg == "off":
            self.stream_chunks = False
            self.stream_typewriter_ms = 0
        else:
            try:
                ms = int(arg)
            except ValueError:
                return  # ignore garbage silently
            if ms < 0:
                ms = 0
            if ms > 500:
                ms = 500
            self.stream_chunks = True
            self.stream_typewriter_ms = ms
        # Persist to on-disk config.
        try:
            cfg = load_config()
            cfg.stream_chunks = self.stream_chunks
            cfg.stream_typewriter_ms = self.stream_typewriter_ms
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
        self._sync_shortcuts_visibility()

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

    def run_from_history(self, ticker: str, flow_id: str) -> None:
        """Called by App.on_rerun_requested when user presses r/Ctrl+Enter
        in the history drill-down view. Sets the prompt and submits a fresh
        f1 run on the same ticker."""
        self.ticker = ticker
        self.flow_id = flow_id
        self.query_one("#prompt", Input).value = f"analyze {ticker}"
        self.run_worker(self.action_submit(), exclusive=False)

    # ------------------------------------------------- ticker-shortcut chip handler
    def on_ticker_shortcuts_pressed(self, event: TickerShortcuts.Pressed) -> None:
        """User clicked a ticker chip on the welcome screen.

        Populate the prompt input with ``analyze <TICKER>`` and submit
        it (same path as a typed Enter). The chip widget hides itself
        via ``_sync_shortcuts_visibility`` once the chat-log has content.
        """
        ticker = event.ticker
        self.ticker = ticker
        self.query_one("#prompt", Input).value = f"analyze {ticker}"
        # Run the submit coroutine without awaiting it here — on_message
        # handlers are sync in textual; the action_submit chain drives its
        # own awaitables.
        self.run_worker(self.action_submit(), exclusive=False)

    def _sync_shortcuts_visibility(self) -> None:
        """Hide the chip row once the chat has content beyond the welcome card; show on empty."""
        try:
            shortcuts = self.query_one("#ticker-shortcuts", TickerShortcuts)
        except Exception:
            return
        log = self.query_one("#chat-log", VerticalScroll)
        # Welcome bubble is the only bubble at first mount. After the user
        # sends a message (or clicks a chip), the user bubble lands as the
        # 2nd child — hide the chips then. Re-show on /clear (action_clear_chat
        # calls _show_welcome → _sync_shortcuts_visibility).
        shortcuts.display = len(log.children) <= 1

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
        if cmd == "stream":
            self.set_stream(arg)
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
            activity.mark_running(event.agent_id, model=event.model)

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
            # Route the strip entry to the bubble registered to the agent that
            # requested the tool. Falls back to `_last_bubble()` (the most
            # recently started agent) for older emitters that omit the field.
            bubble = None
            if event.requested_by_agent is not None:
                bubble = self._bubble_index.get(event.requested_by_agent)
            if bubble is None:
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
            # Same routing rule as ConnectorCompleted.
            bubble = None
            if event.requested_by_agent is not None:
                bubble = self._bubble_index.get(event.requested_by_agent)
            if bubble is None:
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
            activity.mark_finished(
                event.agent_id,
                wallclock_s=event.wallclock_s,
                cost_usd=event.cost_usd_estimate,
                tokens_in=event.in_tokens,
                tokens_out=event.out_tokens,
            )

        elif isinstance(event, CostDelta):
            cost.update_totals(event.cumulative_in, event.cumulative_out, event.cumulative_cost)
            activity.update_cost(event.agent_id, event.cost_usd_estimate,
                                 event.cumulative_cost)

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
                env = event.final_envelope
                memo = env.get("memo", {}) if isinstance(env.get("memo"), dict) else {}
                diff = DiffPanel.maybe_build(prior, {
                    "thesis_text": env.get("thesis_text", ""),
                    "conviction":  str(env.get("conviction", "?")),
                    "confidence":  env.get("confidence", ""),
                    "bottom_line": memo.get("bottom_line", env.get("bottom_line", {})),
                    "bull_case":   memo.get("bull_case", ""),
                    "bear_case":   memo.get("bear_case", ""),
                    "what_an_attacker_would_say": memo.get("what_an_attacker_would_say", ""),
                    "next_three_questions": str(memo.get("next_three_questions", "")),
                    "verification": env.get("verification", {}),
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

        This also kicks off the **lawyer-grade citation binding**: for
        each URL on the chip without a cached snippet, we fire
        ``runtime.citations.ensure_snippet_for_url`` in a thread. When
        each fetch completes, the chat screen posts a
        ``SnippetReady`` message back; the chip updates its
        ``snippet_paths`` and lights up the ◫ badge. Pure side-effect
        -- fire-and-forget; no UI block.
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
            snippet_paths=list(chip.snippet_paths),
            thesis_id=chip.thesis_id,
            version=chip.version,
            timestamp=ts,
        )        # The screen sets its own id in __init__ (idempotent).
        self.app.push_screen(modal)
        # Kick off background snippet-fetch for any naked URL on this
        # chip. No UI block; chip updates on completion.
        self._ensure_snippets_in_background(chip)

    # ---------------------------------------------------------- snippet fetch
    def on_citation_chip_snippet_ready(self, message) -> None:
        """Listen for ``SnippetReady`` and update the chip's snippet_paths.

        Called from the asyncio event loop after a worker thread has
        run ``ensure_snippet_for_url``. We resolve the chip by id,
        splice the new path into ``chip.snippet_paths`` at the right
        index, and call ``chip.set_citations(snippet_paths=...)`` so
        the chip label re-lights.
        """
        try:
            chip = self.query_one(f"#{message.chip_id}", CitationChip)
        except Exception:
            return
        # Build a new snippet_paths list, padding with prior entries.
        cur = list(chip.snippet_paths or [])
        while len(cur) < len(chip.citations or []):
            cur.append(None)
        if 0 <= message.idx < len(cur):
            cur[message.idx] = message.snippet_path if message.ok else None
        chip.set_citations(list(chip.citations), snippet_paths=cur)

    def _ensure_snippets_in_background(self, chip: CitationChip) -> None:
        """For each naked URL on *chip*, fire ``ensure_snippet_for_url``
        in a worker thread. On completion, post ``SnippetReady`` so the
        chip gets updated in the UI thread.

        Concurrency: one task per URL. ``runtime.citations``'s in-memory
        dedupe guarantees the network sees each URL at most once even
        if the user double-clicks the chip. Failures leave the chip's
        snippet_paths[idx] = None, and a toast hint is shown so the user
        knows to ``o``/`y` the URL instead.
        """
        run_id = getattr(self, "_current_run_id", None) or "_chat_default"
        urls = list(chip.citations or [])
        paths = list(chip.snippet_paths or [])
        while len(paths) < len(urls):
            paths.append(None)
        chip_id = chip.id or ""
        async def _kick() -> None:
            for idx, url in enumerate(urls):
                if not url:
                    continue
                if paths[idx]:       # already cached
                    continue
                # Fire-and-forget: do not block loop on slow upstream.
                await self._fetch_one_snippet(chip_id, url, idx, run_id)
        try:
            self.run_worker(_kick(), exclusive=False)
        except Exception:
            # Textual run_worker is a soft DM; fall back to a thread.
            try:
                import threading as _t
                _t.Thread(target=lambda: [
                    self._fetch_one_snippet(chip_id, url, idx, run_id)
                    for idx, url in enumerate(urls)
                    if url and not paths[idx]
                ], daemon=True).start()
            except Exception:
                pass

    async def _fetch_one_snippet(self, chip_id: str, url: str,
                                  idx: int, run_id: str) -> None:
        """Worker-thread wrapper: call cite module, dispatch SnippetReady."""
        import asyncio as _aio
        from runtime import citations as _cite
        loop = _aio.get_event_loop()
        try:
            res = await loop.run_in_executor(
                None, _cite.ensure_snippet_for_url, url, run_id,
            )
        except Exception as e:
            self.post_message(CitationChip.SnippetReady(
                chip_id, url, idx, snippet_path="", ok=False,
            ))
            return
        ok = res.path is not None
        self.post_message(CitationChip.SnippetReady(
            chip_id, url, idx,
            snippet_path=str(res.path) if ok else "",
            ok=ok,
        ))
        if not ok and res.error:
            # Surface a non-blocking toast so the user knows to open in
            # browser instead. Don't flash on every URL — only rarely.
            try:
                self._set_status_flash(
                    f"⚠  snippet unavailable ({url[:32]}…): {res.error}",
                    warn=True, duration_s=2.5,
                )
            except Exception:
                pass

    # ---------------------------------------------------------- chip actions
    def on_citation_chip_action_requested(self, message) -> None:
        """User pressed ``o`` / ``y`` / ``n`` on a focused chip.

        Routes the action to the platform helper and flashes a toast.
        All of these calls go through ``frontend.utils.platform.*``,
        which is monkey-patched in tests so no browser actually launches.

        Actions:
            open    → ``open_in_browser(message.url)``
            copy    → ``copy_to_clipboard(message.url)``
            preview → just an inline reflow of the chip's status; flash OK.
        """
        from frontend.utils import platform as _plat
        try:
            # Resolve chip if present to honour is shorthand; we don't
            # actually need the chip object — the message has the URL.
            pass
        except Exception:
            return
        action = getattr(message, "action", "")
        url = getattr(message, "url", "") or ""
        if action == "open":
            if not url:
                self._set_status_flash("⚠  no URL on this chip — press Enter for the modal", warn=True)
                return
            try:
                ok, msg = _plat.open_in_browser(url)
            except Exception as e:
                ok, msg = False, f"{type(e).__name__}: {e}"
            if ok:
                self._set_status_flash(f"✓ opened: {url}", ok=True, duration_s=3.0)
            else:
                self._set_status_flash(f"✗ browser refused: {msg}", warn=True)
            return
        if action == "copy":
            if not url:
                self._set_status_flash("⚠  no URL on this chip — press Enter for the modal", warn=True)
                return
            try:
                ok, msg = _plat.copy_to_clipboard(url)
            except Exception as e:
                ok, msg = False, f"{type(e).__name__}: {e}"
            if ok:
                self._set_status_flash(f"✓ copied: {url}", ok=True, duration_s=3.0)
            else:
                self._set_status_flash(f"✗ copy failed: {msg}", warn=True)
            return
        if action == "snippet":
            # The chip's `v` key sends a snippet path. Empty/missing
            # means the connector didn't cache one — toast a hint that
            # `o` is the fallback path.
            if not url:
                self._set_status_flash(
                    "⚠  no cached snippet for this citation — "
                    "press `o` to open the URL instead",
                    warn=True,
                )
                return
            try:
                ok, msg = _plat.open_in_pager(url)
            except Exception as e:
                ok, msg = False, f"{type(e).__name__}: {e}"
            if ok:
                self._set_status_flash(f"✓ pager: {msg}", ok=True, duration_s=2.0)
            else:
                self._set_status_flash(f"✗ pager failed: {msg}", warn=True)
            return
        if action == "preview":
            # The chip has already advanced its label; we just confirm.
            if url:
                self._set_status_flash(f"→ {url}", ok=True, duration_s=1.6)
            return
        # Unknown action — silently ignore (future-proofing).
        return

    # ---------------------------------------------------------- internal helpers
    def _on_wizard_done(self, result: str | None) -> None:
        """Called when the welcome wizard is dismissed.
        If the user completed the wizard (result is the model string),
        reload the config and show the welcome card with the new provider.
        """
        if result:
            self.reload_config_from_disk()
        self._update_footer_hint()

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
        self._sync_shortcuts_visibility()

    def _set_banner_warning(self, msg: str) -> None:
        self.query_one(ConnectionBanner).set_warning(msg)

    def _set_banner_ok(self) -> None:
        self.query_one(ConnectionBanner).set_ok()

    def _set_status_flash(
        self,
        msg: str,
        *,
        ok: bool = False,
        warn: bool = False,
        duration_s: float = 0.0,
    ) -> None:
        """Brief transient banner flash.

        Distinct from ``_set_banner_warning`` in that it does NOT
        clobber an active warning if we want a separate ephemeral
        info line. Currently rendered on the same ConnectionBanner
        widget but using the ``info`` style (blue/neutral). When
        ``duration_s > 0`` we schedule an auto-clear that does NOT
        touch any active warning state — the flash simply disappears.

        OK and warn are mutually exclusive — warn takes precedence to
        match the user's mental model of "important <= important+".
        """
        try:
            banner = self.query_one(ConnectionBanner)
        except Exception:
            return
        # Don't step on an active warning: warnings take priority over
        # transient info flashes per the same UX rule used by toast
        # widgets in the existing modal screens.
        if warn and not banner._is_info_active():
            # If a true warning is already up, leave it; surface the
            # warn flash as info so the user still sees it.
            banner.set_info(f"⚠  {msg}")
        else:
            banner.set_info(msg)
        if duration_s > 0:
            try:
                self.set_timer(duration_s, self._clear_status_flash_once)
            except Exception:
                # Headless / off-event-loop path; skip the timer silently.
                pass

    def _clear_status_flash_once(self) -> None:
        """Clear a transient info flash without disturbing a real warning.

        If the banner is currently in ``warn`` or ``error`` mode (i.e.
        the warning was set AFTER our info flash and we're now trying
        to clear the flash back to warning), we call ``set_ok`` which
        would erase it. So guard: if the banner is in info-only mode,
        clear; if a warning is layered on top, leave it.
        """
        try:
            banner = self.query_one(ConnectionBanner)
        except Exception:
            return
        if banner._is_info_active():
            banner.set_ok()

    def _update_footer_hint(self, suffix: str = "") -> None:
        paid = ",".join(self.paid_for) if self.paid_for else "none"
        connector_prefix = self._connector_footer_segment()
        # Predict the cost of one run of `self.flow_id` on `self.model`.
        # For the hybrid case, paid_for means "use Sonnet for those
        # agents" — see docs/runtime/rates.py for the convention.
        try:
            from runtime.rates import format_cost_for_footer  # type: ignore
            cost_segment = format_cost_for_footer(
                self.flow_id,
                self.model,
                paid_for=self.paid_for,
                depth=self.depth,
                per_agent_model=self.per_agent_model or None,
            )
        except Exception:
            cost_segment = "? · ? agents"  # never break the footer
        base = (
            f"{connector_prefix}{self.flow_id} · {self.model} "
            f"· paid-for: {paid} · depth: {self.depth} "
            f"· {cost_segment}"
        )
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
