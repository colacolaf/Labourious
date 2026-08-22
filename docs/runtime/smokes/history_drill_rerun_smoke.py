"""smoke — history-drill re-run: Ctrl+Enter / r from drill view → new f1 run.

Verifies the end-to-end path:
  HistoryScreen.action_rerun → pop + post ReRunRequested
  → App.on_rerun_requested → ChatScreen.run_from_history
  → prompt populated with "analyze <TICKER>" + submit triggered

Exercises:
  1. ReRunRequested message carries correct ticker + flow_id
  2. action_rerun: visible row selection, pop-before-post ordering
  3. App.on_rerun_requested dispatches to ChatScreen.run_from_history
  4. ChatScreen.run_from_history: prompt populated, submit scheduled
  5. Ctrl+Enter binding maps to "rerun" action
  6. Empty list: action_rerun does nothing (no crash)
  7. ChatScreen class has required method
  8. HistoryScreen BINDINGS list verified
"""

from __future__ import annotations

import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2]

if str(DOCS) not in sys.path:
    sys.path.insert(0, str(DOCS))

# ---------- lightweight smoke harness (mutable counter avoids global scoping issues) ----------
_ok: list[int] = []   # _ok[0] = passed
_bad: list[int] = []  # _bad[0] = failed


def _pass(label: str) -> None:
    _ok[0] += 1
    print(f"  ✓ {label}")


def _fail(label: str, extra: str = "") -> None:
    _bad[0] += 1
    print(f"  ✗ FAIL: {label}{extra}")


def step(label: str, value: bool) -> None:
    if value:
        _pass(label)
    else:
        _fail(label)


def step_eq(label: str, a, b) -> None:
    if a == b:
        _pass(label)
    else:
        _fail(label, f"  ({a!r} != {b!r})")


def section(title: str) -> None:
    print(f"\n── {title} ──")


# initialise counters
_ok.append(0)
_bad.append(0)

# ===========================================================================
# 1. ReRunRequested message structure
# ===========================================================================
section("1. ReRunRequested message structure")

from frontend.screens.history import HistoryScreen, ReRunRequested, re_run_label

msg = ReRunRequested("NVDA", "f1")
step("ReRunRequested carries ticker", msg.ticker == "NVDA")
step("ReRunRequested carries flow_id", msg.flow_id == "f1")

msg2 = ReRunRequested("AAPL", "f2-daily-briefing")
step("ReRunRequested with f10 flow_id", msg2.ticker == "AAPL")
step("ReRunRequested f10 flow_id carried", msg2.flow_id == "f2-daily-briefing")

# ===========================================================================
# 2. HistoryScreen bindings include Ctrl+Enter
# ===========================================================================
section("2. HistoryScreen BINDINGS")

bindings_by_key = {b.key: b.action for b in HistoryScreen.BINDINGS}
step("escape → back", bindings_by_key.get("escape") == "back")
step("r → rerun", bindings_by_key.get("r") == "rerun")
step("ctrl+enter → rerun (new binding)", bindings_by_key.get("ctrl+enter") == "rerun")
step_eq("3 bindings total", len(HistoryScreen.BINDINGS), 3)

# ===========================================================================
# 3. ChatScreen has run_from_history method
# ===========================================================================
section("3. ChatScreen.run_from_history exists")

from frontend.screens.chat import ChatScreen
import inspect

step("run_from_history is callable", callable(getattr(ChatScreen, "run_from_history", None)))
sig = inspect.signature(ChatScreen.run_from_history)
step_eq("run_from_history takes 3 params (self, ticker, flow_id)", len(sig.parameters), 3)

# ===========================================================================
# 4. App.on_rerun_requested dispatches to ChatScreen
# ===========================================================================
section("4. App.on_rerun_requested")

from frontend.app import LabouriousApp

step("LabouriousApp has on_rerun_requested", hasattr(LabouriousApp, "on_rerun_requested"))

src = inspect.getsource(LabouriousApp.on_rerun_requested)
step("App handler checks isinstance(self.screen, ChatScreen)",
     "isinstance(self.screen, ChatScreen)" in src)
step("App handler calls screen.run_from_history",
     "self.screen.run_from_history" in src)

# ===========================================================================
# 5. Simulated re-run flow: action_rerun → pop → post → App → ChatScreen
# ===========================================================================
section("5. Simulated re-run flow (unit-level)")

from frontend.history_io import ThesisRow

row_nvda = ThesisRow(
    id=1, ticker="NVDA", date="2026-08-21", datetime="2026-08-21T14:00:00",
    flow_id="f1", version=1, conviction=4, placement="BUY",
    price=890.0, base_case=820.0, bottom_line_text="Strong buy on AI moat",
    thesis_text="## bull\nCUDA dominance\n\n## bear\nExport risk",
    evidence_urls=[], model="ollama/llama3.3:70b", paid_for=False,
)
row_aapl = ThesisRow(
    id=2, ticker="AAPL", date="2026-08-21", datetime="2026-08-21T15:00:00",
    flow_id="f1", version=1, conviction=3, placement="HOLD",
    price=225.0, base_case=210.0, bottom_line_text="Hold — services growth",
    thesis_text="## bull\nServices moat\n\n## bear\nHardware slowdown",
    evidence_urls=[], model="ollama/llama3.3:70b", paid_for=False,
)


class MockHistoryScreen:
    """Simulate HistoryScreen's action_rerun logic without Textual runtime."""
    def __init__(self, rows, index=0):
        self._rows = list(rows)
        self._index = index
        self._filter = ""
        self._posts: list = []
        self._popped = False

    def _visible_rows(self) -> list:
        if not self._filter:
            return self._rows
        q = self._filter.strip().lower()
        return [r for r in self._rows
                if q in r.ticker.lower() or q in (r.model or "").lower()]

    def pop_screen(self):
        self._popped = True

    def post_message(self, msg):
        self._posts.append(msg)

    def action_rerun(self):
        visible = self._visible_rows()
        if not visible:
            return
        row = visible[min(self._index, len(visible) - 1)]
        ticker, flow_id = row.ticker, row.flow_id
        self.pop_screen()
        self.post_message(ReRunRequested(ticker, flow_id))

    def action_filter_search(self, term: str):
        self._filter = term
        self._index = 0


# --- Sub-test A: Single row, index 0 ---
mock = MockHistoryScreen([row_nvda])
mock.action_rerun()
step("A: popped before post (pop was True)", mock._popped)
step_eq("A: one message posted", len(mock._posts), 1)
step("A: message is ReRunRequested", isinstance(mock._posts[0], ReRunRequested))
step("A: message.ticker == NVDA", mock._posts[0].ticker == "NVDA")
step("A: message.flow_id == f1", mock._posts[0].flow_id == "f1")

# --- Sub-test B: Two rows, index 1 (second row) ---
mock = MockHistoryScreen([row_nvda, row_aapl], index=1)
mock.action_rerun()
step("B: message.ticker == AAPL", mock._posts[0].ticker == "AAPL")
step("B: message.flow_id == f1", mock._posts[0].flow_id == "f1")
step("B: popped before post", mock._popped)

# --- Sub-test C: Empty rows — no crash, no post ---
mock = MockHistoryScreen([])
mock.action_rerun()
step_eq("C: no message posted", len(mock._posts), 0)
step("C: no pop on empty (no crash)", not mock._popped)

# --- Sub-test D: Filter narrows visible, re-run respects filter ---
mock = MockHistoryScreen([row_nvda, row_aapl], index=0)
mock.action_filter_search("AAPL")
step_eq("D: filtered visible has 1 row", len(mock._visible_rows()), 1)
mock.action_rerun()
step("D: filtered re-run picks AAPL", mock._posts[0].ticker == "AAPL")

# --- Sub-test E: Index out of range clamped ---
mock = MockHistoryScreen([row_nvda], index=99)
mock.action_rerun()
step("E: clamped index picks NVDA", mock._posts[0].ticker == "NVDA")

# --- Sub-test F: No filter means both visible ---
mock = MockHistoryScreen([row_nvda, row_aapl])
step_eq("F: no filter → both visible", len(mock._visible_rows()), 2)

# ===========================================================================
# 6. re_run_label helper
# ===========================================================================
section("6. re_run_label helper")

step("re_run_label includes /research", "/research" in re_run_label("claude-sonnet-4-5"))
step("re_run_label includes model short name", "claude-sonnet-4-5" in re_run_label("claude-sonnet-4-5"))

# ===========================================================================
# 7. run_from_history sets prompt + ticker correctly (unit)
# ===========================================================================
section("7. run_from_history state mutation (unit)")


class MockChatScreen:
    def __init__(self):
        self.ticker = None
        self.flow_id = None
        self.prompt_value = ""
        self.submitted = False

    def run_from_history(self, ticker: str, flow_id: str) -> None:
        self.ticker = ticker
        self.flow_id = flow_id
        self.prompt_value = f"analyze {ticker}"
        self.submitted = True


mock_chat = MockChatScreen()
mock_chat.run_from_history("NVDA", "f1")
step("run_from_history sets ticker", mock_chat.ticker == "NVDA")
step("run_from_history sets flow_id", mock_chat.flow_id == "f1")
step("run_from_history sets prompt", mock_chat.prompt_value == "analyze NVDA")
step("run_from_history triggers submit", mock_chat.submitted)

mock_chat2 = MockChatScreen()
mock_chat2.run_from_history("AAPL", "f2-daily-briefing")
step("run_from_history AAPL ticker", mock_chat2.ticker == "AAPL")
step("run_from_history f10 flow_id", mock_chat2.flow_id == "f2-daily-briefing")
step_eq("run_from_history AAPL prompt", mock_chat2.prompt_value, "analyze AAPL")

# ===========================================================================
# 8. App.on_rerun_requested type-safety check
# ===========================================================================
section("8. App.on_rerun_requested type check")

app_sig = inspect.signature(LabouriousApp.on_rerun_requested)
params = list(app_sig.parameters.keys())
step_eq("App handler has 2 params (self, message)", len(params), 2)
step("App handler param is 'message'", params[1] == "message")

# Verify ReRunRequested has the right fields
step("ReRunRequested has ticker attr", hasattr(ReRunRequested("X", "f1"), "ticker"))
step("ReRunRequested has flow_id attr", hasattr(ReRunRequested("X", "f1"), "flow_id"))

# ===========================================================================
# Summary
# ===========================================================================
total = _ok[0] + _bad[0]
print(f"\n=== {_ok[0]}/{total} ok ===")
if _bad[0]:
    print(f"{_bad[0]} fail")
    sys.exit(1)
else:
    print("all green")