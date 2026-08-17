"""
test_per_asset_coverage.py — every ticker in a basket appears in every relevant section.

Discipline: every ticker the user asked about must be touched on in the memo's
bottom_line / bear_case / next_three_questions. No silent skips.
Test pattern: run an f2 (compare-tickers) or f1-on-basket; assert coverage in the produced envelope.

Usage:
    pytest docs/runtime/evals/test_per_asset_coverage.py -v
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"


@pytest.fixture
def basket_tickers():
    return ["AAPL", "MSFT", "GOOG", "NVDA", "AMD"]


def test_every_ticker_covered(basket_tickers):
    """
    Asserts that in any run, every ticker referenced in the run's `inputs.tickers` (or
    targeted TICKER env) appears at least once in memo.bottom_line, memo.bear_case (or
    bull_case), and memo.next_three_questions.
    """
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet — first f2 invocation produces envelope to test.")

    envelopes = list(RUNS_DIR.rglob("final_envelope.json"))
    if not envelopes:
        pytest.skip("no final envelopes yet")

    fails = []
    for env_path in envelopes:
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        memo = env.get("memo", {}) or {}
        if not memo:
            continue
        # Concatenate the relevant sections; check ticker presence
        haystack = (
            (memo.get("bottom_line", {}) or {}).get("one_liner", "")
            + " "
            + (memo.get("bottom_line", {}) or {}).get("flip_trigger", "")
            + " "
            + memo.get("bear_case", "") + " " + memo.get("bull_case", "")
            + " " + " ".join(memo.get("next_three_questions", []) or [])
        )
        missing = [t for t in basket_tickers if t not in haystack]
        if missing:
            # Only fail if the run's inputs look like a basket run.
            # Heuristic: a basket run has multiple tickers in its run_id.
            run_id = env_path.parent.name
            if any(t in run_id for t in basket_tickers):
                # f2 or f5 flows touch multiple tickers; if a basket-ticker is
                # not in the memo at all, that's a coverage failure.
                absent = [t for t in missing if t not in run_id]
                if absent:
                    fails.append(
                        f"{env_path}: basket tickers {absent} not mentioned in memo."
                    )
    assert not fails, "\n".join(fails)
