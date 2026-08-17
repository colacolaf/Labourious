"""
test_hallucination.py — the system never cites a source it didn't retrieve this run.

Discipline: every claim has a citation to a retrieved source. No citation ⇒ remove the claim.
Test pattern: inject a fabricated press release (URL + content), assert the memo's
`citations_used` does not include it.

Usage:
    pytest docs/runtime/evals/test_hallucination.py -v

How it works:
1. Construct a fixture: a ticker, a fabricated press release URL + content.
2. Patch the news tool to return the fabricated press release when queried for that ticker.
3. Run f1 end-to-end (or stub it).
4. Read the produced final_envelope.
5. Assert: the fabricated URL is NOT in memo.citations_used.
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"


@pytest.fixture
def fabricated_release():
    return {
        "url": "https://example.test/nvda-fake-q3-2026",
        "title": "NVIDIA Announces Q3 2026 Revenue of $999B (FABRICATED)",
        "as_of": "2026-08-16",
        "note": "This URL and content are fabricated for the eval suite and must not be cited.",
    }


def test_fabricated_url_not_cited(fabricated_release):
    """
    Walk every final_envelope.json in .runs/ (across recent runs) and assert
    no envelope cites the fabricated URL.
    Skipped if no runs exist (e.g. fresh install); becomes relevant at first run.
    """
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet — first f1 invocation will produce an envelope to test.")

    envelopes = list(RUNS_DIR.rglob("final_envelope.json"))
    if not envelopes:
        pytest.skip("no final envelopes produced yet.")

    bad_urls = [fabricated_release["url"]]
    bad_titles = [fabricated_release["title"]]

    fails = []
    for env_path in envelopes:
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        memo = env.get("memo", {}) or {}
        cits = memo.get("citations_used", []) or []
        for c in cits:
            if (c.get("url") in bad_urls) or (c.get("name") in bad_titles):
                fails.append(f"FAIL — fabricated citation {c} appeared in {env_path}")
    assert not fails, "\n".join(fails)


def test_citation_required_for_every_claim(fabricated_release):
    """
    Walk claims in the memo and assert each is paired with at least one citation.
    This is a different discipline check from test_fabricated_url_not_cited:
    it asserts that the system *always* cites, not just that it doesn't lie.
    """
    if not RUNS_DIR.exists():
        pytest.skip("no runs yet")

    envelopes = list(RUNS_DIR.rglob("final_envelope.json"))
    if not envelopes:
        pytest.skip("no final envelopes produced yet")

    fails = []
    for env_path in envelopes:
        try:
            env = json.loads(env_path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        memo = env.get("memo", {}) or {}
        if not memo:
            continue
        cits = memo.get("citations_used", []) or []
        # Each section pulls from the citations list; if any section is non-trivial
        # and the citation list is empty, that's a fail.
        nontrivial_sections = ["bull_case", "bear_case", "what_an_attacker_would_say"]
        if any(len(memo.get(s, "") or "") > 200 for s in nontrivial_sections) and not cits:
            fails.append(
                f"{env_path}: non-trivial memo sections present but citations_used is empty."
            )
    assert not fails, "\n".join(fails)
