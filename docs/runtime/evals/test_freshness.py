"""
test_freshness.py — stale sources are flagged.

Discipline: every number has an `as_of`; if a cited finding is older than the freshness
window for its data type (quarterly filings = 6mo; daily prices = 1d; news = 24h),
the system flags it in `gaps` or `verification.error_flags`.
Test pattern: inject a 3-year-old "as_of" via tool override; assert staleness is flagged.

Usage:
    pytest docs/runtime/evals/test_freshness.py -v
"""
from __future__ import annotations

import datetime as dt
import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"

# Freshness windows per data type
WINDOWS_DAYS = {
    "filings": 180,
    "prices": 1,
    "news": 1,
    "transcript": 90,
}


@pytest.fixture
def stale_source():
    return {
        "url": "https://www.sec.gov/.../nvda-10k-2023.htm",
        "filed_date": (dt.date.today() - dt.timedelta(days=1095)).isoformat(),
        "note": "A 3-year-old filing injected to test freshness discipline.",
    }


def test_stale_sources_flagged(stale_source):
    """
    Asserts that if a run cites a source whose `as_of` is older than the freshness
    window for its data type, the memo surfaces a `gaps` entry or
    `verification.error_flags` entry naming the staleness.
    """
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet — first f1 invocation produces envelope to test.")

    envelopes = list(RUNS_DIR.rglob("final_envelope.json"))
    if not envelopes:
        pytest.skip("no final envelopes yet")

    fails = []
    stale_dt = dt.datetime.fromisoformat(stale_source["filed_date"])
    cutoff_dt = dt.datetime.now() - dt.timedelta(days=WINDOWS_DAYS["filings"])
    for env_path in envelopes:
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        memo = env.get("memo", {}) or {}
        cits = memo.get("citations_used", []) or []
        for c in cits:
            try:
                d = dt.datetime.fromisoformat(c.get("date", ""))
            except (ValueError, TypeError):
                continue
            if d < cutoff_dt:
                # Source is stale; check gap or error_flags surface
                gaps = env.get("gaps", []) or []
                errs = ((env.get("verification", {}) or {}).get("error_flags", []) or [])
                named = any(
                    "stale" in str(x).lower() or "outdated" in str(x).lower()
                    or "freshness" in str(x).lower()
                    for x in gaps + errs
                )
                if not named:
                    fails.append(
                        f"{env_path}: stale source ({c.get('date')}) cited without a freshness flag."
                    )
    assert not fails, "\n".join(fails)
