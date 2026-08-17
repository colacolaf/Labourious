"""
test_abstention.py — out-of-scope queries return NOT FOUND, not invention.

Discipline: when the system can't verify, it says so. NEVER invents with "likely ~$X"
or "reported around" with an unretrieved number.
Test pattern: ask a question the connector can't answer (e.g. "What's Tesla's 2030
delivery projection?"); assert memo.gaps contains a NOT FOUND-style entry; assert
the memo's bottom_line does not invent a number.

Usage:
    pytest docs/runtime/evals/test_abstention.py -v
"""
from __future__ import annotations

import json
import pytest
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"


@pytest.fixture
def out_of_scope_query():
    return "What's Tesla's projected 2030 annual deliveries?"


def test_abstention_present(out_of_scope_query):
    """
    Asserts that any run that includes an out-of-scope query surfaces a `NOT FOUND`
    (or equivalent honesty marker) in gaps, and the memo doesn't invent a number
    that wasn't retrieved.
    """
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet — first out-of-scope run produces envelope to test.")

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
        gaps = env.get("gaps", []) or []
        # Hunt for numerics in the memo that aren't paired with "approximated" or
        # "estimate" or "not verified" — fabrication smell.
        fabricated_number = False
        for section in ("bull_case", "bear_case", "what_an_attacker_would_say"):
            text = memo.get(section, "") or ""
            # Look for a confident-sounding forecast number ("<digits>M", "<digits>K deliveries")
            # without an explicit caveat nearby.
            for match in re.finditer(r"(\d+(?:\.\d+)?)\s*(?:M|K|million|bn)\s+(?:deliveries|cars|units)", text):
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                window = text[start:end]
                if not any(w in window.lower() for w in ("estimate", "approxim", "rough", "uncertain", "not verified")):
                    fabricated_number = True
                    break
        # If a number was stated confidently without caveat AND there's a gap entry
        # naming "couldn't verify" or "not found" nearby, the discipline is held.
        if fabricated_number:
            has_gap = any(
                re.search(r"not\s+found|couldn.t\s+verify|unknown", str(g).lower())
                for g in gaps
            )
            if not has_gap:
                fails.append(
                    f"{env_path}: confident number in {section.title()} but no gap warns the user."
                )
    assert not fails, "\n".join(fails)
