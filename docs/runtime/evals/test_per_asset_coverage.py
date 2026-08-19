"""
test_per_asset_coverage.py — every ticker in a basket appears in the relevant sections.

Discipline: every ticker the user asked about must be touched on in the memo's
bottom_line / bear_case / bull_case / next_three_questions. No silent skips.

How it works:
- The test walks every ``final_envelope.json`` under ``docs/runtime/.runs/``.
- It only evaluates envelopes whose ``flow_id`` is in ``BASKET_FLOWS`` —
  i.e. flows that produce a real cohort output (``f2`` compare, ``f5`` sector,
  ``f6`` screen).
- For each basket envelope, the ``tickers`` field is the authoritative basket.
  Every basket ticker must appear in at least one of: ``memo.bottom_line``,
  ``memo.bull_case``, ``memo.bear_case``, ``memo.next_three_questions`` (i.e.
  the memo isn't silent about any cohort member).

Usage:
    pytest docs/runtime/evals/test_per_asset_coverage.py -v
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"

# Flows whose output must touch every ticker it claimed to cover.
BASKET_FLOWS = {"f2", "f5", "f6"}


@pytest.fixture
def basket_tickers():
    """Default basket for ad-hoc coverage checks against standalone flows.
    Used only when the test is invoked with --tickers-style harness overrides.
    """
    return ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN"]


def _haystack(env: dict) -> str:
    memo = env.get("memo", {}) or {}
    return (
        " ".join(str(v) for v in (memo.get("bottom_line", {}) or {}).values() if v)
        + " " + (memo.get("bull_case", "") or "")
        + " " + (memo.get("bear_case", "") or "")
        + " " + (memo.get("what_an_attacker_would_say", "") or "")
        + " " + " ".join(memo.get("next_three_questions", []) or [])
    )


def test_every_basket_ticker_covered():
    """
    Strict check on flows that produce a real basket output:
    every ticker declared in ``env.tickers`` must be mentioned somewhere in
    the memo. Skipped when no runs exist.
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
        if env.get("flow_id") not in BASKET_FLOWS:
            continue  # single-ticker flows (f1/f3/f4/f7/f8/f9) aren't subject to this rule.

        declared = env.get("tickers") or []
        if not declared:
            continue
        haystack = _haystack(env)
        missing = [t for t in declared if t not in haystack]
        if missing:
            fails.append(
                f"{env_path}: basket tickers {missing} not mentioned in any "
                f"section of memo (flow={env.get('flow_id')})."
            )
    assert not fails, "\n".join(fails)


def test_single_ticker_runs_stay_single():
    """
    Counter-discipline: f1 / f3 / f4 / f7 / f8 / f9 (single-ticker flows)
    MUST NOT silently expand to a multi-ticker output. If ``tickers`` is
    declared alongside ``ticker``, flag it.
    """
    SINGLE_TICKER_FLOWS = {"f1", "f3", "f4", "f7", "f8", "f9"}
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet — first invocation produces envelope to test.")
    envelopes = list(RUNS_DIR.rglob("final_envelope.json"))
    if not envelopes:
        pytest.skip("no final envelopes yet")

    fails = []
    for env_path in envelopes:
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if env.get("flow_id") not in SINGLE_TICKER_FLOWS:
            continue
        if env.get("tickers") and len(env["tickers"]) > 1:
            fails.append(
                f"{env_path}: single-ticker flow {env['flow_id']} has "
                f"tickers={env['tickers']} (should be a single ticker)."
            )
    assert not fails, "\n".join(fails)
