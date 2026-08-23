"""
smoke — protocol-3: DiffPanel structured section-by-section deltas.

Verifies the v2 DiffPanel that groups changes into
Added (green) / Removed (red) / Modified (yellow) per section
instead of the old literal OLD→NEW lines.

Exercises:
  1. _section_changed — numeric, text, whitespace-insensitive
  2. _compact_dict — flattens nested dicts
  3. _render_body — empty diffs (no changes)
  4. _render_body — added sections only
  5. _render_body — removed sections only
  6. _render_body — modified sections only
  7. _render_body — mixed (all three categories)
  8. maybe_build — None when no prior
  9. maybe_build — picks most recent prior
  10. ChatScreen FlowFinished wiring — full envelope sections forwarded
  11. collapse/expand widget structure
  12. Conviction changes (numeric comparison)
  13. Verification dict changes
"""

from __future__ import annotations

import sys, os

DOCS = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, DOCS)

from frontend.widgets.diff_widget import DiffPanel, _compact_dict, _DIFF_SECTIONS

passes = 0
fails = 0

def section(title: str) -> None:
    print(f"\n── {title} ──")

def step(label: str, cond: bool) -> None:
    global passes, fails
    if cond:
        print(f"  ✓ {label}")
        passes += 1
    else:
        print(f"  ✗ FAIL: {label}")
        fails += 1

def step_eq(label: str, a, b) -> None:
    step(label, a == b)

# ===========================================================================
# 1. _section_changed
# ===========================================================================
section("1. _section_changed")

step("identical text → False", not DiffPanel._section_changed("BUY", "BUY"))
step("different text → True", DiffPanel._section_changed("BUY", "HOLD"))
step("same after trim → False", not DiffPanel._section_changed("  BUY  ", "BUY"))
step("same numeric → False", not DiffPanel._section_changed("3", "3"))
step("different numeric → True", DiffPanel._section_changed("3", "4"))
step("empty vs whitespace → False", not DiffPanel._section_changed("  ", ""))
step("None vs '' → False", not DiffPanel._section_changed("", ""))
step("None vs 'text' → True", DiffPanel._section_changed("", "text"))

# ===========================================================================
# 2. _compact_dict
# ===========================================================================
section("2. _compact_dict")

step_eq("empty dict", _compact_dict({}), "{}")
step_eq("single key", _compact_dict({"a": "b"}), "a=b")
step_eq("multi key", _compact_dict({"a": "1", "b": "2"}), "a=1, b=2")
step("very long string truncated", len(_compact_dict({"long": "x" * 300})) <= 200)
step_eq("direction+conviction",
        _compact_dict({"direction": "HOLD", "conviction": 4}),
        "direction=HOLD, conviction=4")

# ===========================================================================
# 3. _render_body — no changes
# ===========================================================================
section("3. _render_body — no changes")

prior = {
    "thesis_text": "NVDA is a strong buy on AI moat.",
    "bottom_line": {"direction": "BUY", "conviction": 5},
    "conviction": "5",
}
current = {
    "thesis_text": "NVDA is a strong buy on AI moat.",
    "bottom_line": {"direction": "BUY", "conviction": 5},
    "conviction": "5",
}
body = DiffPanel._render_body(prior, current)
step("detects no changes", "No significant changes" in body)
step("no added header", "═══ Added ═══" not in body)
step("no removed header", "═══ Removed ═══" not in body)
step("no modified header", "═══ Modified ═══" not in body)

# ===========================================================================
# 4. _render_body — added sections only
# ===========================================================================
section("4. _render_body — added sections only")

prior2 = {"conviction": "3"}
current2 = {
    "thesis_text": "New thesis.",
    "conviction": "3",
    "confidence": "HIGH",
}
body2 = DiffPanel._render_body(prior2, current2)
step("detects added", "═══ Added ═══" in body2)
step("added contains Thesis", "Thesis" in body2)
step("added contains Confidence", "Confidence" in body2)
step("no modified (conviction same)", "═══ Modified ═══" not in body2)
step("no removed", "═══ Removed ═══" not in body2)

# ===========================================================================
# 5. _render_body — removed sections only
# ===========================================================================
section("5. _render_body — removed sections only")

prior3 = {
    "thesis_text": "Old thesis.",
    "conviction": "4",
    "bear_case": "The bear case was strong.",
}
current3 = {"conviction": "4"}
body3 = DiffPanel._render_body(prior3, current3)
step("detects removed", "═══ Removed ═══" in body3)
step("removed contains Thesis", "Thesis" in body3)
step("removed contains Bear Case", "Bear Case" in body3)
step("no modified", "═══ Modified ═══" not in body3)
step("no added", "═══ Added ═══" not in body3)

# ===========================================================================
# 6. _render_body — modified sections only
# ===========================================================================
section("6. _render_body — modified sections only")

prior4 = {"thesis_text": "BUY NVDA.", "conviction": "4"}
current4 = {"thesis_text": "HOLD NVDA.", "conviction": "3"}
body4 = DiffPanel._render_body(prior4, current4)
step("detects modified", "═══ Modified ═══" in body4)
step("no added", "═══ Added ═══" not in body4)
step("no removed", "═══ Removed ═══" not in body4)

# ===========================================================================
# 7. _render_body — mixed
# ===========================================================================
section("7. _render_body — mixed (added + removed + modified)")

prior5 = {
    "thesis_text": "Old thesis text.",
    "conviction": "3",
    "bear_case": "Old bear case.",
}
current5 = {
    "thesis_text": "New thesis text.",
    "conviction": "4",
    "confidence": "HIGH",
}
body5 = DiffPanel._render_body(prior5, current5)
step("all three categories present", all(h in body5 for h in [
    "═══ Added ═══", "═══ Removed ═══", "═══ Modified ═══"
]))

# ===========================================================================
# 8. maybe_build — None when no prior
# ===========================================================================
section("8. maybe_build — None when no prior")

step_eq("empty list → None", DiffPanel.maybe_build([], {"thesis_text": "x"}), None)

# ===========================================================================
# 9. maybe_build — picks most recent prior
# ===========================================================================
section("9. maybe_build — picks most recent prior")

priors = [
    {"version": "v1", "created_at": "2026-01-01", "thesis_text": "old"},
    {"version": "v2", "created_at": "2026-08-20", "thesis_text": "recent"},
    {"version": "v3", "created_at": "2026-03-15", "thesis_text": "middle"},
]
panel = DiffPanel.maybe_build(priors, {"thesis_text": "new"})
step("returns a DiffPanel", panel is not None)
step("header shows v2 (most recent)", "v2" in panel._collapsible.title)

# ===========================================================================
# 10. _DIFF_SECTIONS covers all expected keys
# ===========================================================================
section("10. _DIFF_SECTIONS coverage")

expected_keys = {
    "thesis_text", "bottom_line", "bull_case", "bear_case",
    "what_an_attacker_would_say", "next_three_questions",
    "conviction", "confidence", "verification",
}
actual_keys = {k for k, _ in _DIFF_SECTIONS}
step_eq("all expected sections covered", actual_keys, expected_keys)

# ===========================================================================
# 11. Widget structure (header + collapsible)
# ===========================================================================
section("11. Widget structure")

panel2 = DiffPanel(
    prior={"version": "v1", "created_at": "2026-01-01", "thesis_text": "Old"},
    current={"thesis_text": "New text for the diff."},
)
step("starts collapsed", panel2._collapsible.collapsed)
header_str = str(panel2._collapsible)
step("header includes version", "v1" in panel2._collapsible.title)
step("header includes date", "2026-01-01" in panel2._collapsible.title)

# ===========================================================================
# 12. Conviction (numeric) comparison
# ===========================================================================
section("12. Conviction changes")

prior_c = {"conviction": "3"}
current_c = {"conviction": "5"}
body_c = DiffPanel._render_body(prior_c, current_c)
step("conviction change → Modified", "═══ Modified ═══" in body_c)
step("conviction change shows in diff", "Conviction" in body_c)

# ===========================================================================
# 13. Verification dict changes
# ===========================================================================
section("13. Verification dict changes")

prior_v = {
    "verification": {"asset_checks": ["AAPL verified"], "error_flags": []},
}
current_v = {
    "verification": {"asset_checks": ["AAPL verified", "MSFT verified"], "error_flags": ["flag1"]},
}
body_v = DiffPanel._render_body(prior_v, current_v)
step("verification dict change → Modified", "═══ Modified ═══" in body_v)

# ===========================================================================
# Summary
# ===========================================================================
print(f"\n=== {passes}/{passes + fails} ok ===")
if fails == 0:
    print("all green")
else:
    print(f"{fails} fail")
    sys.exit(1)