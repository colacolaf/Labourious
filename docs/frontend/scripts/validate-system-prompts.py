#!/usr/bin/env python3
"""
Validate every Labourious HQ system prompt against the quality framework.

Usage:
    python3 validate-system-prompts.py                 # check docs/frontend tree
    python3 validate-system-prompts.py <dir-or-file>   # check a specific path
    python3 validate-system-prompts.py --list          # list detected tiers only

Exit codes:
    0  all prompts pass
    1  one or more prompts failed
    2  no system prompts found / usage error

Checks per prompt (tier-aware):

  Tier detection (by content, in priority order):
    - T4 intern : has "## Data Extraction Protocol"
    - T1/T2 lead: has "## Asset Validation Protocol" (leads & named agents)
    - T3 utility : has "## Data Quality Protocol" and "## Data Freshness:"
      (T2 straggler Markopolos carries the full T1/T2 set and is caught above)

  1. PROTOCOLS     — each tier requires its full protocol set (see tables below)
  2. PER-ASSET GATE— the prompt must force checking every stock/fund every time
                     (T1/T2: "MUST be validated EVERY time"; T3/T4: "never skip one")
  3. FRESHNESS     — T3/T4 must declare "## Data Freshness: <tier>" with a valid tier;
                     T1/T2 inherit freshness from the PM briefing and are exempt
  4. FROM/TO       — output must be addressed FROM <agent> TO <recipient>

  Note: the PM Bodyguard (penthouse) is validated as a T3 agent — it carries Data
  Quality + Error Detection protocols, a "## Data Freshness: Real-time" section,
  a per-asset coverage gate, and FROM/TO headers in its interrupt template.

Required sections by tier:

  T1/T2 (leads & named):
    ## Quality Assurance Protocol
    ## Asset Validation Protocol
    ## Source Verification Protocol
    ## Connector Usage Protocol
    ## Error Detection & Correction Protocol

  T3 (utility):
    ## Data Quality Protocol
    ## Error Detection Protocol

  T4 (intern):
    ## Data Extraction Protocol
    ## Instruction Following Protocol
    ## Error Flagging Protocol
    ## Humility Protocol
    ## Data Quality Protocol
    ## Error Detection Protocol
"""

from __future__ import annotations

import argparse
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_ROOT = os.path.join(PROJECT_ROOT, "docs", "frontend")

VALID_FRESHNESS_TIERS = {
    "Real-time", "Intraday", "Daily", "Weekly", "Quarterly", "Annual", "Any",
}

T1_T2_REQUIRED = [
    "## Quality Assurance Protocol",
    "## Asset Validation Protocol",
    "## Source Verification Protocol",
    "## Connector Usage Protocol",
    "## Error Detection & Correction Protocol",
]

T3_REQUIRED = [
    "## Data Quality Protocol",
    "## Error Detection Protocol",
]

T4_REQUIRED = [
    "## Data Extraction Protocol",
    "## Instruction Following Protocol",
    "## Error Flagging Protocol",
    "## Humility Protocol",
    "## Data Quality Protocol",
    "## Error Detection Protocol",
]

PER_ASSET_PATTERNS = [
    # T3/T4 standard phrasing
    re.compile(r"never skip one", re.IGNORECASE),
    # T1/T2 canonical phrasing: "Every ticker/security ... MUST be validated EVERY time"
    re.compile(r"validated EVERY time", re.IGNORECASE),
    # T1/T2 variant: "For EVERY asset/transaction/company mentioned in your analysis, you MUST validate"
    re.compile(r"EVERY\s+[\w/&.\-]+(?:\s+[\w/&.\-]+){0,5}\s+mentioned", re.IGNORECASE),
]

FRESHNESS_RE = re.compile(r"^## Data Freshness:\s*(.+)$", re.MULTILINE)


def find_prompts(root: str) -> list[str]:
    """Return all system-prompt.md files under root (or root itself if a file)."""
    if os.path.isfile(root):
        return [root]
    prompts = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name == "system-prompt.md":
                prompts.append(os.path.join(dirpath, name))
    return sorted(prompts)


def detect_tier(text: str, path: str) -> str:
    """Classify a prompt by content. Returns one of: T4, T1/T2, T3, special."""
    if "## Data Extraction Protocol" in text:
        return "T4"
    if "## Asset Validation Protocol" in text:
        return "T1/T2"
    if "## Data Quality Protocol" in text and "## Data Freshness:" in text:
        return "T3"
    # T2 straggler (e.g. Harry Markopolos) uses Data Quality but no freshness
    if "## Data Quality Protocol" in text:
        return "T1/T2"
    return "unknown"


def has_per_asset_gate(text: str) -> bool:
    return any(p.search(text) for p in PER_ASSET_PATTERNS)


def freshness_check(text: str) -> tuple[bool, str]:
    m = FRESHNESS_RE.search(text)
    if not m:
        return False, "missing '## Data Freshness: <tier>' heading"
    tier = m.group(1).strip()
    # tier may be followed by a sentence on the same line
    tier_word = tier.split()[0].rstrip(":")
    if tier_word not in VALID_FRESHNESS_TIERS:
        return False, f"invalid freshness tier '{tier_word}' (valid: {', '.join(sorted(VALID_FRESHNESS_TIERS))})"
    return True, tier_word


def validate_prompt(path: str) -> tuple[str, bool, list[str]]:
    """Run all checks against one prompt. Returns (tier, passed, failure reasons)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()

    tier = detect_tier(text, path)
    failures: list[str] = []

    # 1. Protocols
    if tier == "T1/T2":
        for section in T1_T2_REQUIRED:
            if section not in text:
                failures.append(f"missing required section: {section}")
    elif tier == "T3":
        for section in T3_REQUIRED:
            if section not in text:
                failures.append(f"missing required section: {section}")
    elif tier == "T4":
        for section in T4_REQUIRED:
            if section not in text:
                failures.append(f"missing required section: {section}")
    else:
        failures.append("unable to detect tier (no known protocol markers)")

    # 2. Per-asset gate
    if not has_per_asset_gate(text):
        failures.append("missing per-asset gate ('never skip one' / 'validated EVERY time')")

    # 3. Freshness
    if tier in ("T3", "T4"):
        ok, detail = freshness_check(text)
        if not ok:
            failures.append(f"freshness: {detail}")

    # 4. FROM/TO
    if "FROM:" not in text:
        failures.append("missing 'FROM:' in output format")
    if "TO:" not in text:
        failures.append("missing 'TO:' in output format")

    return tier, (len(failures) == 0), failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Labourious HQ system prompts")
    parser.add_argument("path", nargs="?", default=DEFAULT_ROOT,
                        help="file or directory to check (default: docs/frontend)")
    parser.add_argument("--list", action="store_true", help="list prompts with detected tier, no checks")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"error: path not found: {args.path}", file=sys.stderr)
        return 2

    prompts = find_prompts(args.path)
    if not prompts:
        print(f"error: no system-prompt.md files found under {args.path}", file=sys.stderr)
        return 2

    total = len(prompts)
    passed = 0
    failed = 0
    counts: dict[str, int] = {}

    print(f"Validating {total} system prompts under {args.path}\n")

    for path in prompts:
        rel = os.path.relpath(path, PROJECT_ROOT)
        if args.list:
            with open(path, encoding="utf-8") as f:
                text = f.read()
            tier = detect_tier(text, path)
            counts[tier] = counts.get(tier, 0) + 1
            print(f"  [{tier:<6}] {rel}")
            continue

        tier, ok, failures = validate_prompt(path)
        counts[tier] = counts.get(tier, 0) + 1

        if ok:
            passed += 1
            print(f"  PASS  [{tier:<6}] {rel}")
        else:
            failed += 1
            print(f"  FAIL  [{tier:<6}] {rel}")
            for reason in failures:
                print(f"          - {reason}")

    print()
    print(f"Tier breakdown: " + ", ".join(f"{t}={c}" for t, c in sorted(counts.items())))
    print(f"Result: {passed} passed, {failed} failed (of {total})")

    if args.list:
        print("\n(no checks run — list mode)")
        return 0

    if failed:
        print("\nFAILURES DETECTED — see above for remediation.")
        return 1
    print("\nAll prompts passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
