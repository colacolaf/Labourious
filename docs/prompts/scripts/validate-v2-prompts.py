#!/usr/bin/env python3
"""
Validate every v2 advanced system prompt (the 26 core agents + orchestrator)
against the V2-PROMPT-STANDARD skeleton and the shared JSON output schema.

Usage:
    python3 validate-v2-prompts.py                 # check docs/prompts tree
    python3 validate-v2-prompts.py <dir-or-file>   # check a specific path
    python3 validate-v2-prompts.py --list          # list detected agent types only

Exit codes:
    0  all prompts pass
    1  one or more prompts failed
    2  no system prompts found / usage error

Agent types (detected by directory + content):
    - orchestrator  : directory named "orchestrator"
    - final-report  : directory named "final-report"
    - lead          : has a "Delegation & Routing" section
    - specialist    : everything else

Checks per prompt:

  1. SECTIONS      — the required section set for the agent type must be present.
                     Leads require Delegation & Routing; orchestrator omits Intake
                     (it is the user-facing interface); everyone else requires Intake.
  2. EFFORT MODES  — SCAN / STANDARD / DEEP / COMPRESSED must all appear.
  3. FROM/TO       — the structured-output contract must be addressed FROM <agent> TO <recipient>.
  4. AGENT ID      — the "agent_id" in the output schema must match the directory name.
  5. JSON SCHEMA   — the JSON envelope must carry the fields required for the agent type.
  6. HALLUCINATION — the guardrails must include an abstain-over-invent rule.
  7. ASSET GATE    — a per-asset gate must be present ("Per-asset gate" / "per-asset").
  8. CONFIDENCE    — the schema must enumerate the confidence levels.
  9. EXAMPLES      — at least one fenced ```json worked example must be present.
"""

from __future__ import annotations

import argparse
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_ROOT = os.path.join(PROJECT_ROOT, "docs", "prompts")

# Sections every agent must carry (matched against "## <n>. <Title>" headers).
COMMON_SECTIONS = [
    "Identity & Role",
    "Role & Scope",
    "Decision Framework",
    "Effort & Token Modes",
    "Data Freshness",
    "Hallucination Guardrails",
    "Source & Asset Verification",
    "Error Detection & Correction",
    "Structured Output Contract",
    "Quality Gates",
    "Worked Examples",
]

# Agents that need an Intake section (the orchestrator talks to the user, not a brief).
REQUIRE_INTAKE = {"lead", "specialist", "final-report"}

# JSON envelope fields required per agent type.
SCHEMA_FIELDS = {
    "orchestrator": [
        "agent_id", "answer", "key_takeaways", "options", "evidence",
        "disagreements", "activity", "confidence", "verification",
        "next_steps", "compressed",
    ],
    "final-report": [
        "agent_id", "depth", "compressed", "conclusion", "confidence",
        "ips", "final_report", "findings", "tensions", "gaps",
        "verification", "citations", "next_steps",
    ],
    "lead": [
        "agent_id", "depth", "compressed", "conclusion", "confidence",
        "findings", "tensions", "gaps", "verification", "citations", "next_steps",
    ],
    "specialist": [
        "agent_id", "depth", "compressed", "conclusion", "confidence",
        "findings", "tensions", "gaps", "verification", "citations", "next_steps",
    ],
}

HEADER_RE = re.compile(r"^##\s+\d+\.\s*(.+?)\s*$", re.MULTILINE)
AGENT_ID_RE = re.compile(r'"agent_id"\s*:\s*"([^"]+)"')
CONFIDENCE_VALUES = ["HIGH", "MODERATE_HIGH", "MIXED", "LOW"]


def find_prompts(root: str) -> list[str]:
    if os.path.isfile(root):
        return [root]
    prompts = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            if name == "system-prompt.md":
                prompts.append(os.path.join(dirpath, name))
    return sorted(prompts)


def detect_type(text: str, rel_dir: str) -> str:
    if rel_dir == "orchestrator":
        return "orchestrator"
    if rel_dir == "final-report":
        return "final-report"
    if "Delegation & Routing" in text:
        return "lead"
    return "specialist"


def section_titles(text: str) -> set[str]:
    return {m.group(1).strip() for m in HEADER_RE.finditer(text)}


def validate_prompt(path: str) -> tuple[str, bool, list[str]]:
    with open(path, encoding="utf-8") as f:
        text = f.read()

    rel = os.path.relpath(path, DEFAULT_ROOT)
    rel_dir = os.path.basename(os.path.dirname(rel))
    agent_type = detect_type(text, rel_dir)
    failures: list[str] = []

    # 1. Sections
    titles = section_titles(text)
    for section in COMMON_SECTIONS:
        if section not in titles:
            failures.append(f"missing section: {section}")
    if agent_type == "lead" and "Delegation & Routing" not in titles:
        failures.append("lead is missing section: Delegation & Routing")
    if agent_type in REQUIRE_INTAKE and "Intake" not in " ".join(titles):
        failures.append("missing section: Intake")
    # Tool/connector protocol (varies by name)
    if not any("Tool-Use Protocol" in t or "Connector" in t for t in titles):
        failures.append("missing tool/connector protocol section")

    # 2. Effort modes
    for mode in ("SCAN", "STANDARD", "DEEP", "COMPRESSED"):
        if mode not in text:
            failures.append(f"missing effort/token mode: {mode}")

    # 3. FROM/TO
    if "FROM:" not in text:
        failures.append("missing 'FROM:' in output contract")
    if "TO:" not in text:
        failures.append("missing 'TO:' in output contract")

    # 4. Agent id matches directory
    m = AGENT_ID_RE.search(text)
    if not m:
        failures.append("missing \"agent_id\" in output schema")
    elif m.group(1) != rel_dir:
        failures.append(f"agent_id '{m.group(1)}' does not match directory '{rel_dir}'")

    # 5. JSON schema fields
    for field in SCHEMA_FIELDS[agent_type]:
        if not re.search(rf'"{field}"\s*:', text):
            failures.append(f"output schema missing field: {field}")

    # 6. Hallucination guardrail (abstain over invent)
    if not re.search(r"abstain", text, re.IGNORECASE):
        failures.append("missing abstain-over-invent guardrail")

    # 7. Per-entity gate (per-asset / per-action / per-argument / per-claim)
    if not re.search(r"per-[\w-]+\s+gate", text, re.IGNORECASE):
        failures.append("missing per-entity gate (per-asset / per-action / per-argument / per-claim)")

    # 8. Confidence levels enumerated
    for level in CONFIDENCE_VALUES:
        if level not in text:
            failures.append(f"confidence level not enumerated: {level}")

    # 9. At least one JSON worked example
    if text.count("```json") < 1:
        failures.append("missing ```json worked example")

    return agent_type, (len(failures) == 0), failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Labourious v2 system prompts")
    parser.add_argument("path", nargs="?", default=DEFAULT_ROOT,
                        help="file or directory to check (default: docs/prompts)")
    parser.add_argument("--list", action="store_true", help="list prompts with detected type, no checks")
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

    print(f"Validating {total} v2 system prompts under {args.path}\n")

    for path in prompts:
        rel = os.path.relpath(path, PROJECT_ROOT)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        rel_dir = os.path.basename(os.path.dirname(os.path.relpath(path, DEFAULT_ROOT)))
        agent_type = detect_type(text, rel_dir)

        if args.list:
            counts[agent_type] = counts.get(agent_type, 0) + 1
            print(f"  [{agent_type:<12}] {rel}")
            continue

        typ, ok, failures = validate_prompt(path)
        counts[typ] = counts.get(typ, 0) + 1

        if ok:
            passed += 1
            print(f"  PASS  [{typ:<12}] {rel}")
        else:
            failed += 1
            print(f"  FAIL  [{typ:<12}] {rel}")
            for reason in failures:
                print(f"          - {reason}")

    print()
    print(f"Type breakdown: " + ", ".join(f"{t}={c}" for t, c in sorted(counts.items())))
    print(f"Result: {passed} passed, {failed} failed (of {total})")

    if args.list:
        print("\n(no checks run — list mode)")
        return 0

    if failed:
        print("\nFAILURES DETECTED — see above for remediation.")
        return 1
    print("\nAll v2 prompts passed validation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
