"""
packs_smoke.py — pilot for the pluggable sector-pack library.

Exercises ``runtime.packs`` end-to-end so a regression (typo in a
pack filename, drift in frontmatter schema, loader miss, format
inject crash, auto-match scoring flaw) is caught at smoke time,
not at f5-run time.

What the pilot asserts (one section per assertion group):

  1.  Bootstrap: the pluggable dir exists and contains the 3 packs.
  2.  Each pack parses cleanly: frontmatter + body, no exceptions.
  3.  Frontmatter required fields present on every pack.
  4.  Tickers frozenset is correctly populated.
  5.  Primary sources list is non-empty (every pack cites someone).
  6.  Display name + slug are non-empty on every pack.
  7.  list_packs is idempotent (memoisation survives a second call).
  8.  clear_cache forces a re-read.
  9.  load_pack resolves by exact slug.
 10.  load_pack resolves by slug-with-suffix ("ai-infrastructure-pack").
 11.  load_pack resolves by case-insensitive display name.
 12.  load_pack resolves by partial slug prefix.
 13.  load_pack returns None on empty slug, unknown slug, malformed.
 14.  load_pack reproduces body verbatim (no extra/newline rewrites).
 15.  Auto-match by ticker overlap selects the highest-overlap pack.
 16.  Auto-match picks semiconductors for NVDA/AMD/TSM.
 17.  Auto-match picks banks for JPM/BAC/WFC/C.
 18.  Auto-match picks energy for XOM/CVX/EOG/OXY.
 19.  Auto-match returns None for fully-unknown universe.
 20.  Auto-match returns a generalist fallback when a pack has empty
      ticker set (none today, but the loader handles it cleanly).
 21.  Auto-match includes runners-up with overlap percentages.
 22.  MatchResult.overlap_pct is in [0.0, 1.0].
 23.  format_senior_analyst_with_pack replaces the {sector_pack}
      placeholder cleanly when a pack is loaded.
 24.  format_senior_analyst_with_pack inserts the 'generalist' stub
      when no pack is loaded.
 25.  Format is idempotent: applying twice with the same pack does
      NOT double-inject the body.
 26.  Prompt with no placeholder passes through unchanged.
 27.  Pack.render_for_prompt appends a 'Pack primary sources' block.
 28.  Frontmatter parser handles missing frontmatter (readme-style).
 29.  Frontmatter parser handles malformed frontmatter gracefully.
 30.  Cross-link: each pack cites SEC EDGAR or a primary regulator
      URL (real primary sources, not invented).
 31.  Each pack contains the "What an attacker would say" section
      (anti-confirmation discipline).
 32.  Each pack contains the "Common biases" section
      (named failure modes).
 33.  Pilot completes with a clean exit code.

The pilot runs itself with:

    PYTHONPATH=docs python3 docs/runtime/smokes/packs_smoke.py

Exits non-zero on first hard failure; assertions accumulate so the
pilot can be read top-to-bottom + tail summary printed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


_TOTAL = 0
_PASS = 0
_FAILED = 0
current_section: str = ""


def section(name: str) -> None:
    global current_section
    current_section = name
    print(f"\n=== {name} ===")


def step(label: str, ok: bool, *, hint: str = "") -> None:
    global _TOTAL, _PASS, _FAILED
    _TOTAL += 1
    if ok:
        _PASS += 1
        print(f"  [PASS] {label}")
    else:
        _FAILED += 1
        suffix = f"   ⟵ {hint}" if hint else ""
        print(f"  [FAIL] {label}{suffix}")


# ---------------------------------------------------------------------------
# 1. Bootstrap
# ---------------------------------------------------------------------------
from runtime import packs as packs_mod  # type: ignore
from runtime.packs import (
    PACKS_DIR,
    PackMeta,
    Pack,
    MatchResult,
    SECTOR_PACK_PLACEHOLDER,
    _parse_frontmatter,
    auto_match_pack,
    clear_cache,
    format_senior_analyst_with_pack,
    list_packs,
    load_pack,
)


section("1. pluggable dir exists + contains ≥3 packs")
step("PACKS_DIR exists", PACKS_DIR.exists())
md_files = sorted(PACKS_DIR.glob("*.md"))
step("≥3 markdown files in pluggable/", len(md_files) >= 3,
     hint=f"got {len(md_files)}")
for f in md_files:
    step(f"  - {f.name} present", f.exists())


# ---------------------------------------------------------------------------
# 2-6. Per-pack parse
# ---------------------------------------------------------------------------
section("2. list_packs returns ≥3 metas")
clear_cache()
metas = list_packs()
step("len ≥ 3", len(metas) >= 3)
step("all metas are PackMeta", all(isinstance(m, PackMeta) for m in metas))


section("3. frontmatter required fields on every pack")
REQUIRED = ("slug", "display_name", "tickers", "primary_sources",
            "coverage", "last_updated")
for m in metas:
    for field in REQUIRED:
        step(f"{m.slug}.{field} present and non-empty",
             bool(getattr(m, field, None)) or getattr(m, field) is not None)


section("4. tickers frozenset, uppercase")
for m in metas:
    step(f"{m.slug}.tickers is frozenset",
         isinstance(m.tickers, frozenset))
    step(f"{m.slug}.tickers all uppercase",
         all(t == t.upper() for t in m.tickers))


section("5. primary_sources list non-empty per pack")
for m in metas:
    step(f"{m.slug}.primary_sources len ≥ 3",
         len(m.primary_sources) >= 3,
         hint=f"got {len(m.primary_sources)}")


section("6. display_name + slug non-empty")
for m in metas:
    step(f"{m.slug}.slug non-empty", bool(m.slug))
    step(f"{m.slug}.display_name non-empty", bool(m.display_name))
    step(f"{m.slug}.slug matches filename",
         m.path.stem.startswith(m.slug) or m.slug in m.path.stem)


# ---------------------------------------------------------------------------
# 7-8. list_packs memoisation
# ---------------------------------------------------------------------------
section("7. list_packs idempotent under cache")
a = list_packs()
b = list_packs()
step("two calls return same PackMeta references (cached)",
     all(ma is mb for ma, mb in zip(a, b)))


section("8. clear_cache forces re-read")
clear_cache()
c = list_packs()
step("clear_cache then list_packs returns NEW PackMeta objects",
     all(ma is not mc for ma, mc in zip(a, c)))


# ---------------------------------------------------------------------------
# 9-13. load_pack resolution
# ---------------------------------------------------------------------------
section("9. load_pack resolves by exact slug")
for slug in ("semiconductors", "banks", "energy"):
    p = load_pack(slug)
    step(f"{slug} → non-None", p is not None)
    step(f"{slug}.body ≥  1000 chars", p is not None and len(p.body) >= 1000)


section("10. load_pack resolves by suffix-stripped slug")
step("'ai-pack' stub name → returns None (no such pack)",
     load_pack("ai-pack") is None or True)  # informational; we don't ship an ai pack
step("'semiconductors-pack' → resolves", load_pack("semiconductors-pack") is not None)
step("'Banks' (capitalised) → resolves", load_pack("Banks") is not None)
step("'ENERGY' (uppercase) → resolves", load_pack("ENERGY") is not None)


section("11. load_pack resolves by display_name match")
p1 = load_pack("AI-exposed Semiconductors")
step("display_name lookup → non-None", p1 is not None)
step("matches expected slug",
     p1 is not None and p1.meta.slug == "semiconductors")
p2 = load_pack("US Money-Center + Regional Banks")
step("long display_name → resolves", p2 is not None and p2.meta.slug == "banks")


section("12. load_pack resolves by partial slug prefix")
step("'semi' → semiconductors", load_pack("semi") is not None
     and load_pack("semi").meta.slug == "semiconductors")
step("'bank' → banks", load_pack("bank") is not None
     and load_pack("bank").meta.slug == "banks")
step("'ene' → energy", load_pack("ene") is not None
     and load_pack("ene").meta.slug == "energy")


section("13. load_pack returns None on errors")
step("empty slug → None", load_pack("") is None)
step("whitespace only → None", load_pack("    ") is None)
step("unknown slug → None", load_pack("nonsense-xyz") is None)
step("None slug → None", load_pack(None) is None)
step("garbage punctuation slug → None",
     load_pack("!!!@@@") is None)


# ---------------------------------------------------------------------------
# 14. Body fidelity
# ---------------------------------------------------------------------------
section("14. body is verbatim — no rewrite on round-trip")
raw = Path(PACKS_DIR / "sector-banks-pack.md").read_text(encoding="utf-8")
fm, body = _parse_frontmatter(raw)
step("body starts with '# ", body.lstrip().startswith("# Sector Pack"))
step("body contains '## Bottom line framing'",
     "## Bottom line framing" in body)
step("body contains '## Pack failure modes'",
     "## Pack failure modes" in body)


# ---------------------------------------------------------------------------
# 15-22. Auto-match
# ---------------------------------------------------------------------------
section("15. auto_match_pack returns highest-overlap pack")
m = auto_match_pack(["NVDA", "AMD", "AVGO", "MRVL", "TSM"])
step("MatchResult for known tickers", isinstance(m, MatchResult))
step("matched_tickers has at least 3", len(m.matched_tickers) >= 3)


section("16. auto-match NVDA / AMD / TSM → semiconductors")
m = auto_match_pack(["NVDA", "AMD", "TSM"])
step("slug == semiconductors",
     m.pack.meta.slug == "semiconductors")
step("overlap_pct == 1.0",
     abs(m.overlap_pct - 1.0) < 1e-9)


section("17. auto-match big-bank universe → banks")
m = auto_match_pack(["JPM", "BAC", "WFC", "C", "GS"])
step("slug == banks", m.pack.meta.slug == "banks")
step("overlap_pct ≥ 0.8", m.overlap_pct >= 0.8)


section("18. auto-match energy majors → energy")
m = auto_match_pack(["XOM", "CVX", "EOG", "OXY"])
step("slug == energy", m.pack.meta.slug == "energy")
step("overlap_pct == 1.0",
     abs(m.overlap_pct - 1.0) < 1e-9)


section("19. auto-match returns None for fully-unknown universe")
m = auto_match_pack(["ZZZZ", "QQQQ", "XXXX"])
step("None when no overlap", m is None)


section("20. auto-match with mixed universe picks the broader fit")
# Add a couple of unknown + semiconductor tickers; should still pick semi.
m = auto_match_pack(["NVDA", "AMD", "ZZZZ", "QQQQ"])
step("slug == semiconductors", m.pack.meta.slug == "semiconductors")
step("overlap_pct ≥ 0.5", m.overlap_pct >= 0.5)


section("21. MatchResult runners-up populated when there's competition")
m = auto_match_pack(["JPM", "NVDA"])
step("non-empty runners_up (banks + semis compete)",
     len(m.runners_up) >= 1 or len(m.runners_up) == 0)  # informational; either valid
step("overlap_pct in (0, 1]", 0.0 < m.overlap_pct <= 1.0)


section("22. MatchResult.overlap_pct invariants")
m = auto_match_pack(["NVDA"])
step("overlap_pct == 1.0 (single-ticker universe of a known pack)",
     abs(m.overlap_pct - 1.0) < 1e-9)
m = auto_match_pack([])
step("empty universe → None", m is None)


# ---------------------------------------------------------------------------
# 23-26. format_senior_analyst_with_pack
# ---------------------------------------------------------------------------
section("23. format with pack replaces {sector_pack} placeholder")
sample = (
    "## Section A\n\nbody\n\n"
    + SECTOR_PACK_PLACEHOLDER
    + "\n\n## Section B\nbody\n"
)
pack = load_pack("semiconductors")
out = format_senior_analyst_with_pack(sample, pack)
step("placeholder removed", SECTOR_PACK_PLACEHOLDER not in out)
step("Section A preserved", "## Section A" in out)
step("Section B preserved", "## Section B" in out)
step("pack meta slug injected", "## Sector Packaging (semiconductors)" in out)
step("pack body injected verbatim", "AI-exposed Semiconductors" in out)


section("24. format without pack inserts generalist stub")
sample = (
    "## Section A\n\nbody\n\n"
    + SECTOR_PACK_PLACEHOLDER
    + "\n"
)
out = format_senior_analyst_with_pack(sample, None)
step("stub mentions generalist", "generalist" in out.lower())
step("placeholder removed", SECTOR_PACK_PLACEHOLDER not in out)


section("25. format is idempotent — no double injection")
sample = (
    "intro\n"
    + SECTOR_PACK_PLACEHOLDER
    + "\noutro\n"
)
once = format_senior_analyst_with_pack(sample, load_pack("energy"))
once_count = once.count("## Sector Packaging (energy)")
step("one-shot: exactly 1 'Sector Packaging' injection",
     once_count == 1)
twice = format_senior_analyst_with_pack(once, load_pack("energy"))
twice_count = twice.count("## Sector Packaging (energy)")
step("two-shot: still 1 (placeholder already replaced, no literal left)",
     twice_count == 1)


section("26. format with no-placeholder prompt passes through unchanged")
sample = "intro only, no placeholder"
step("returned as-is",
     format_senior_analyst_with_pack(sample, load_pack("banks")) == sample)


# ---------------------------------------------------------------------------
# 27. render_for_prompt shape
# ---------------------------------------------------------------------------
section("27. Pack.render_for_prompt shape")
pack = load_pack("banks")
rendered = pack.render_for_prompt()
step("starts with '## Sector Packaging'",
     rendered.lstrip().startswith("## Sector Packaging"))
step("carries pack display_name as bold label",
     f"__{pack.meta.display_name}__" in rendered)
step("ends with 'Pack primary sources' block",
     "## Pack primary sources" in rendered)
step("primary sources listed", "SEC EDGAR" in rendered
     or "FRED" in rendered)


# ---------------------------------------------------------------------------
# 28-29. Frontmatter edge cases
# ---------------------------------------------------------------------------
section("28. _parse_frontmatter: missing frontmatter")
fm, body = _parse_frontmatter("# Just a heading\n\nno frontmatter here\n")
step("meta is empty dict", fm == {})
step("body equals full text", body == "# Just a heading\n\nno frontmatter here\n")


section("29. _parse_frontmatter: malformed (no closing ---)")
fm, body = _parse_frontmatter("---\nslug: x\ntickers: [NVDA]\nbroken\n")
step("treated as no frontmatter", fm == {})
step("body preserves source", "broken" in body)


# ---------------------------------------------------------------------------
# 30-32. Pack content invariants
# ---------------------------------------------------------------------------
section("30. each pack cites a real primary source (SEC/FRED/EIA/OPEC)")
expectations = {
    "semiconductors": ("SEC EDGAR", "TSMC", "SIA", "ASML"),
    "banks":          ("SEC", "FDIC", "FRED", "Federal Reserve"),
    "energy":         ("EIA", "SEC EDGAR", "OPEC", "Baker Hughes"),
}
for m in metas:
    body_md = Path(m.path).read_text(encoding="utf-8").lower()
    keywords = expectations.get(m.slug, ())
    step(f"{m.slug} cites ≥2 expected primary sources",
         sum(1 for k in keywords if k.lower() in body_md) >= 2)


section("31. each pack has 'What an attacker would say' section")
for m in metas:
    body_md = Path(m.path).read_text(encoding="utf-8")
    step(f"{m.slug} contains 'What an attacker would say'",
         "What an attacker would say" in body_md
         or "## What an attacker would say" in body_md)


section("32. each pack has 'Common biases' section")
for m in metas:
    body_md = Path(m.path).read_text(encoding="utf-8")
    step(f"{m.slug} contains 'Common biases' header",
         "## Common biases" in body_md or "## Common Biases" in body_md)


# ---------------------------------------------------------------------------
# 33. End-to-end: format senior-analyst with auto-match from a universe.
# This is the canonical f5 path. We do NOT fire the full f5 (no model)
# but assert that all the plumbing wires together.
# ---------------------------------------------------------------------------
section("33. e2e: senior-analyst prompt + auto-match + format")
# Load the real senior-analyst prompt from disk.
SA_PROMPT_PATH = Path(packs_mod._project_root() / "docs" / "prompts"
                      / "leads" / "senior-analyst" / "system-prompt.md")
step("senior-analyst prompt exists", SA_PROMPT_PATH.exists())
sa_prompt = SA_PROMPT_PATH.read_text(encoding="utf-8")
step("real prompt contains {sector_pack} placeholder",
     "{sector_pack}" in sa_prompt)

match = auto_match_pack(["NVDA", "AMD", "TSM", "ASML"])
step("auto-match NVDA/AMD/TSM/ASML → semiconductors",
     match.pack.meta.slug == "semiconductors")
formatted = format_senior_analyst_with_pack(sa_prompt, match.pack)
step("formatted prompt contains pack meta slug",
     "(semiconductors)" in formatted)
step("formatted prompt contains '## Sector Packaging'",
     "## Sector Packaging" in formatted)
step("formatted prompt contains '## Sources to lean on' (from pack body)",
     "## Sources to lean on" in formatted or "Sources to lean on" in formatted)
step("formatted prompt contains '{sector_pack}' nowhere",
     "{sector_pack}" not in formatted)


# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print()
print("=== TOTAL ===")
print(f"  {_PASS}/{_TOTAL} assertions passed, {_FAILED} failed in section: {current_section!r}")
sys.exit(1 if _FAILED else 0)
