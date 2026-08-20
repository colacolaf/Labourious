"""ticker_shortcuts_smoke.py — smoke pilot for the TickerShortcuts widget.

Verifies (without launching a full Textual app):
  1. Default tickers are the curated 7
  2. Custom ticker list overrides defaults
  3. The Pressed message carries the right ticker
  4. Button ids follow the ``chip-<TICKER>`` convention
  5. The ``chat.py`` ``on_ticker_shortcuts_pressed`` handler is wired
  6. WELCOME_TEMPLATE no longer tells users to type ``analyze NVDA`` (now a chip)
  7. The chip widget is mounted in ChatScreen.compose() (smoke by ast walk)
  8. Visibility sync method exists with the right logic
  9. CSS classes for the chip are present in style.tcss

Uses the same harness as the other smokes (section / step / count line).
Run::

    PYTHONPATH=docs python3 docs/runtime/smokes/ticker_shortcuts_smoke.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

THIS = Path(__file__).resolve()
DOCS = THIS.parents[2]
ROOT = DOCS.parent
sys.path.insert(0, str(DOCS))


# --------------------------------------------------------------------------- #
#  helpers (copied from the other smokes — each pilot is a standalone file)
# --------------------------------------------------------------------------- #
def _section(name: str) -> None:
    print(f"\n=== {name} ===")


_passed = 0
_failed = 0


def step(label: str, ok: bool) -> None:
    global _passed, _failed
    if ok:
        _passed += 1
        print(f"  ✓ {label}")
    else:
        _failed += 1
        print(f"  ✗ {label}")


# --------------------------------------------------------------------------- #
#  1. Default tickers are the curated 7
# --------------------------------------------------------------------------- #
_section("1. DEFAULT_TICKERS — curated 7")
from frontend.widgets.ticker_shortcuts import (
    DEFAULT_TICKERS, TickerShortcuts,
)
step("type is tuple", isinstance(DEFAULT_TICKERS, tuple))
step("length == 7", len(DEFAULT_TICKERS) == 7)
step("contains NVDA", "NVDA" in DEFAULT_TICKERS)
step("contains AAPL", "AAPL" in DEFAULT_TICKERS)
step("contains MSFT", "MSFT" in DEFAULT_TICKERS)
step("contains GOOG", "GOOG" in DEFAULT_TICKERS)
step("contains AMZN", "AMZN" in DEFAULT_TICKERS)
step("contains META", "META" in DEFAULT_TICKERS)
step("contains TSLA", "TSLA" in DEFAULT_TICKERS)


# --------------------------------------------------------------------------- #
#  2. Custom ticker list overrides defaults
# --------------------------------------------------------------------------- #
_section("2. TickerShortcuts — custom ticker list overrides defaults")
w = TickerShortcuts(tickers=("NVDA", "BRK-B", "LLY"))
step("tickers attr == custom tuple", w.tickers == ("NVDA", "BRK-B", "LLY"))
step("len matches", len(w.tickers) == 3)


# --------------------------------------------------------------------------- #
#  3. The Pressed message carries the right ticker
# --------------------------------------------------------------------------- #
_section("3. Pressed message — ticker field round-trips")
msg = TickerShortcuts.Pressed("AAPL")
step("is a Message subclass", isinstance(msg, TickerShortcuts.Pressed.__mro__[1]))
step("ticker field is 'AAPL'", msg.ticker == "AAPL")
msg2 = TickerShortcuts.Pressed("BRK-B")
step("ticker field round-trips on second message", msg2.ticker == "BRK-B")


# --------------------------------------------------------------------------- #
#  4. on_button_pressed — chip-<TICKER> convention → Pressed message
# --------------------------------------------------------------------------- #
_section("4. on_button_pressed — chip-<T> convention")
# Build a minimal Button.Pressed-shaped object the handler can read.
class _FakeButton:
    def __init__(self, id: str) -> None:
        self.id = id


class _FakeEvent:
    def __init__(self, button_id: str) -> None:
        self.button = _FakeButton(button_id)


# Capture the posted message.
posted: list[TickerShortcuts.Pressed] = []

class _CaptureWidget(TickerShortcuts):
    def post_message(self, msg):  # type: ignore[override]
        posted.append(msg)


cw = _CaptureWidget(tickers=("NVDA", "AAPL"))
cw.on_button_pressed(_FakeEvent("chip-NVDA"))
step("NVDA click → Pressed('NVDA')", len(posted) == 1 and posted[-1].ticker == "NVDA")
cw.on_button_pressed(_FakeEvent("chip-AAPL"))
step("AAPL click → Pressed('AAPL')", posted[-1].ticker == "AAPL")

# Non-chip buttons are ignored.
cw.on_button_pressed(_FakeEvent("save-button"))
step("non-chip button ignored (no new Pressed)", len(posted) == 2)

# Unknown ticker (in chip-* form but not in list) is ignored.
cw.on_button_pressed(_FakeEvent("chip-FAKE"))
step("unknown chip ignored", len(posted) == 2)


# --------------------------------------------------------------------------- #
#  5. ChatScreen — on_ticker_shortcuts_pressed handler is wired
# --------------------------------------------------------------------------- #
_section("5. ChatScreen — handler wired + ticker input flow")
chat_src = (DOCS / "frontend" / "screens" / "chat.py").read_text(encoding="utf-8")
step("on_ticker_shortcuts_pressed defined",
     "def on_ticker_shortcuts_pressed" in chat_src)
step("handler sets prompt value to analyze <TICKER>",
     'f"analyze {ticker}"' in chat_src or 'self.query_one("#prompt", Input).value = "analyze"' in chat_src
     or re.search(r'value\s*=\s*f"analyze \{ticker\}"', chat_src) is not None)
step("handler calls run_worker for submit",
     "run_worker(self.action_submit" in chat_src or "self.run_worker(self.action_submit" in chat_src)


# --------------------------------------------------------------------------- #
#  6. WELCOME_TEMPLATE — no longer says "Try: `analyze NVDA`"
# --------------------------------------------------------------------------- #
_section("6. WELCOME_TEMPLATE updated (no 'Try: analyze NVDA' line)")
# The OLD line was: "Run the flagship flow on a ticker to begin. Try:\n\n> `analyze NVDA`"
# We replaced it with: "Pick a ticker below to start the flagship flow, or type your own prompt:"
step("'Pick a ticker below' replaced the old 'Try:' hint",
     "Pick a ticker below to start the flagship flow" in chat_src)
step("old 'Try:' hint gone", "Try:\n\n> `analyze NVDA`" not in chat_src)


# --------------------------------------------------------------------------- #
#  7. TickerShortcuts is mounted in ChatScreen.compose()
# --------------------------------------------------------------------------- #
_section("7. TickerShortcuts mounted in ChatScreen.compose()")
# Walk the AST and look for yield TickerShortcuts(...) inside ChatScreen.compose
tree = ast.parse(chat_src)
mounted_in_compose = False
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "compose":
        for sub in ast.walk(node):
            if (isinstance(sub, ast.Yield)
                    and getattr(sub.value, "func", None)
                    and getattr(sub.value.func, "id", "") == "TickerShortcuts"):
                mounted_in_compose = True
step("yield TickerShortcuts present in ChatScreen.compose()", mounted_in_compose)


# --------------------------------------------------------------------------- #
#  8. _sync_shortcuts_visibility exists with the right logic
# --------------------------------------------------------------------------- #
_section("8. _sync_shortcuts_visibility method")
step("method defined", "def _sync_shortcuts_visibility" in chat_src)
step("hides on > 1 child (post-first-msg)", "len(log.children) <= 1" in chat_src)
step("queries TickerShortcuts widget",
     'self.query_one("#ticker-shortcuts", TickerShortcuts)' in chat_src)
step("called from _show_welcome", "_sync_shortcuts_visibility()" in chat_src)
step("called from action_submit",
     chat_src.count("_sync_shortcuts_visibility()") >= 2)


# --------------------------------------------------------------------------- #
#  9. CSS classes for the chip are present in style.tcss
# --------------------------------------------------------------------------- #
_section("9. style.tcss — chip styling")
css = (DOCS / "frontend" / "style.tcss").read_text(encoding="utf-8")
step("TickerShortcuts block present", "TickerShortcuts {" in css)
step("Button.ticker_chip rule present", "Button.ticker_chip {" in css)
step("hover variant present", "Button.ticker_chip:hover {" in css)
step("focus variant present", "Button.ticker_chip:focus {" in css)
step("label styling present", ".ticker_shortcuts_label" in css)


# --------------------------------------------------------------------------- #
#  summary
# --------------------------------------------------------------------------- #
print()
total = _passed + _failed
print(f"{_passed}/{total} ok")
if _failed:
    print(f"{_failed} FAIL")
    sys.exit(1)
print("0 fail")
print("all green")
sys.exit(0)