"""
smoke — decision ledger (weights.py).

Verifies the canonical weighted-synthesis arithmetic that the TUI orchestrator
and the app's graph-collapse both use.

Exercises:
  1. Canonical table: 5 voters, weight sum 85, non-voters carry no weight
  2. Full alignment (all HIGH) -> lean 1.0, LEAN_BULL
  3. Mixed reads -> CONTESTED under the 0.60 band
  4. Attachment scaling: fewer attached agents -> each vote carries more scale
  5. Abstention excludes the agent from numerator AND denominator
  6. LOW confidence cannot drive a verdict alone
  7. forensic-accounting FLAGGED caps the verdict to CONTESTED
  8. devils-advocate caps aggregate confidence to MIXED (never flips verdict)
  9. sentiment never moves lean (weight 0) — only annotates when opposing
  10. UNKNOWN reads abstain (excluded), FLAT/NEUTRAL read as informed neutral
"""

from __future__ import annotations

import os
import sys

DOCS = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, DOCS)

from runtime.weights import (
    WEIGHTS, NON_VOTING_ROLES, CONF_MULT, LEAN_BAND,
    direction_sign, compute_ledger,
)

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


def mk(agent_id: str, confidence: str, **section) -> dict:
    env = {
        "agent_id": agent_id,
        "depth": "STANDARD",
        "compressed": False,
        "confidence": confidence,
        "findings": [],
        "gaps": [],
        "verification": {},
        "citations": [],
        "next_steps": [],
    }
    env.update(section)
    return env


def senior(action: str, confidence: str = "HIGH") -> dict:
    return mk("senior-analyst", confidence, thesis={"bottom_line": {"action": action}})


def quant(low: float, high: float, confidence: str = "HIGH") -> dict:
    return mk("quant", confidence, valuation={"range": {"low": low, "high": high}})


def macro(treatment: str, confidence: str = "HIGH") -> dict:
    return mk("macro", confidence, macro_context={"regime_treatment": treatment})


def technical(bias: str, confidence: str = "HIGH") -> dict:
    return mk("technical", confidence, technical_analysis={"bias": bias})


def flow(net: str, confidence: str = "HIGH") -> dict:
    return mk("flow-and-transcript", confidence, flow_and_transcript={"insider": {"net": net}})


PRICE = 200.0  # inside quant's [180, 215] when used


# ===========================================================================
# 1. Canonical table
# ===========================================================================
section("1. canonical table")
step_eq("5 voters", len(WEIGHTS), 5)
step_eq("raw weight total 85 (NOT normalized to 1)", sum(WEIGHTS.values()), 85)
step("quant 25", WEIGHTS["quant"] == 25)
step("sentiment carries no weight", "sentiment" not in WEIGHTS)
step("forensic is an audit cap, not a voter", "forensic-accounting" not in WEIGHTS)
step("devils-advocate is escalation, not a voter", "devils-advocate" not in WEIGHTS)
step_eq("confidence multipliers", CONF_MULT["HIGH"], 1.0)
step_eq("LEAN_BAND 0.60", LEAN_BAND, 0.60)

# ===========================================================================
# 2. full alignment -> LEAN_BULL 1.0
# ===========================================================================
section("2. full alignment")
envs = {
    "senior-analyst": senior("BUY"),
    "quant": quant(180, 215),          # price 200 < 180? no; 200 is inside [180,215]
    "technical": technical("BULLISH"),
    "flow-and-transcript": flow("BUY"),
}
# price inside range -> quant reads neutral (0); still in denominator
led = compute_ledger(envs, price=200.0)
step("senior contributes 30", any(c.agent_id == "senior-analyst" and c.contribution == 30 for c in led.contributions))
step("quant inside range -> informed neutral 0", any(c.agent_id == "quant" and c.direction == 0 for c in led.contributions))
step("macro not attached -> absent", "macro" not in led.attached)

envs_full = {
    "senior-analyst": senior("BUY"),
    "quant": quant(220, 280),          # price 200 < low -> undervalued -> +1
    "macro": macro("FAVORABLE"),
    "technical": technical("BULLISH"),
    "flow-and-transcript": flow("BUY"),
}
led = compute_ledger(envs_full, price=200.0)
step("lean == 1.0 aligned", abs(led.lean - 1.0) < 1e-9)
step("verdict LEAN_BULL", led.verdict == "LEAN_BULL")
step("aggregate confidence HIGH", led.confidence == "HIGH")
over = compute_ledger({"quant": quant(100, 150)}, price=200.0)  # price above range
step("price above range -> quant bearish (-1)", any(
    c.agent_id == "quant" and c.direction == -1 for c in over.contributions))

# ===========================================================================
# 3. mixed reads -> CONTESTED
# ===========================================================================
section("3. mixed reads")
envs_mixed = {
    "senior-analyst": senior("BUY"),       # +30
    "quant": quant(100, 215),             # neutral (in range) -> 0, ±25 scale
    "macro": macro("NEUTRAL"),            # 0
    "technical": technical("BEARISH", "LOW"),  # -10*0.25 = -2.5
}
led = compute_ledger(envs_mixed, price=200.0)
step("lean below bull band", led.lean < 0.60)
step("verdict CONTESTED", led.verdict == "CONTESTED")
step("technical LOW scaled to -2.5", any(c.agent_id == "technical" and abs(c.contribution - (-2.5)) < 1e-9 for c in led.contributions))

# ===========================================================================
# 4. attachment scaling — fewer attached => each vote carries more scale
# ===========================================================================
section("4. attachment scaling")
only_two = {"senior-analyst": senior("BUY"), "technical": technical("BULLISH")}
led2 = compute_ledger(only_two, price=200.0)
step("two-agent graph full lean 1.0", abs(led2.lean - 1.0) < 1e-9)
only_senior = {"senior-analyst": senior("BUY")}
led3 = compute_ledger(only_senior, price=200.0)
step("single-agent graph denominator 30", led3.denominator == 30)
step("single-agent full lean 1.0", abs(led3.lean - 1.0) < 1e-9)

# ===========================================================================
# 5. abstention — data FAILED / absent excluded from numerator AND denominator
# ===========================================================================
section("5. abstention exclusion")
macro_failed = {"macro": mk("macro", "LOW")}  # macro with no macro_context -> no read
led_abstain = compute_ledger({"senior-analyst": senior("BUY"),
                              "macro": mk("macro", "LOW")}, price=200.0)
step("abstained macro not in denominator", led_abstain.denominator == 30)
step("abstained macro not attached", "macro" not in led_abstain.attached)
step("lean unaffected by abstainer", abs(led_abstain.lean - 1.0) < 1e-9)

# ===========================================================================
# 6. LOW confidence cannot drive a verdict alone
# ===========================================================================
section("6. LOW confidence")
led_low = compute_ledger({"senior-analyst": senior("BUY", "LOW")}, price=200.0)
step("LOW contribution 7.5", abs(led_low.numerator - 7.5) < 1e-9)
step("LOW-only lean 0.25 -> CONTESTED", led_low.verdict == "CONTESTED")

# ===========================================================================
# 7. forensic FLAGGED denies the verdict
# ===========================================================================
section("7. forensic audit")
envs_flag = dict(envs_full)
envs_flag["forensic-accounting"] = mk("forensic-accounting", "HIGH", verdict="FLAGGED")
led_flag = compute_ledger(envs_flag, price=200.0)
step("verdict flipped to CONTESTED by cap", led_flag.confirmed_verdict == "CONTESTED")
step("cap recorded", any("forensic" in c for c in led_flag.caps))

clean = mk("forensic-accounting", "HIGH", verdict="CLEAN")
led_clean = compute_ledger({**envs_full, "forensic-accounting": clean}, price=200.0)
step("CLEAN audit leaves verdict alone", led_clean.confirmed_verdict == "LEAN_BULL")

# ===========================================================================
# 8. devils-advocate caps confidence, never flips verdict
# ===========================================================================
section("8. devils-advocate escalation")
da = mk("devils-advocate", "HIGH",
        fragile_assumption="Adjusted growth below 25%.",
        base_rates=[{"claim": "62% mean-revert", "evidence": "n=14"}])
led_da = compute_ledger({**envs_full, "devils-advocate": da}, price=200.0)
step("verdict stays LEAN_BULL (DA cannot flip)", led_da.confirmed_verdict == "LEAN_BULL")
step("confidence capped to MIXED", led_da.confidence == "MIXED")
step("cap recorded", any("devils-advocate" in c for c in led_da.caps))
da_weak = mk("devils-advocate", "LOW",
             fragile_assumption="A hunch.",
             base_rates=[])
led_da_weak = compute_ledger({**envs_full, "devils-advocate": da_weak}, price=200.0)
step("unsourced DA does not cap", led_da_weak.confidence == "HIGH" and led_da_weak.confirmed_verdict == "LEAN_BULL")

# ===========================================================================
# 9. sentiment weight 0 — never moves the lean
# ===========================================================================
section("9. sentiment weight 0")
base = {"senior-analyst": senior("BUY", "MODERATE_HIGH"), "macro": macro("NEUTRAL")}
led_base = compute_ledger(base, price=200.0)
sent_bull = mk("sentiment", "HIGH",
               sentiment={"signal_tier": "STRONG", "bull_share": 0.9})
led_sent = compute_ledger({**base, "sentiment": sent_bull}, price=200.0)
step("sentiment adds nothing to lean", abs(led_sent.lean - led_base.lean) < 1e-9)
step("denominator unchanged (-30)", led_sent.denominator == led_base.denominator)
sent_bear = mk("sentiment", "LOW",
               sentiment={"signal_tier": "STRONG", "bull_share": 0.1})
led_sent_opp = compute_ledger({**base, "sentiment": sent_bear}, price=200.0)
step("opposing STRONG sentiment warns, still weight 0",
     led_sent_opp.lean == led_base.lean and any("sentiment" in w for w in led_sent_opp.warnings))

# ===========================================================================
# 10. UNKNOWN abstains; FLAT/NEUTRAL are informed neutrals
# ===========================================================================
section("10. neutral vs abstain")
env_unknown = {"technical": technical("UNKNOWN")}
led_u = compute_ledger(env_unknown, price=200.0)
step("UNKNOWN -> abstains (NO_SIGNAL)", led_u.verdict == "NO_SIGNAL")
env_flat = {"flow-and-transcript": flow("FLAT")}
led_f = compute_ledger(env_flat, price=200.0)
step("FLAT -> informed neutral: in denominator, lean 0, CONTESTED",
     led_f.denominator == 10 and led_f.lean == 0.0 and led_f.verdict == "CONTESTED")

env_neutral = {"technical": technical("NEUTRAL")}
led_n = compute_ledger(env_neutral, price=200.0)
step("NEUTRAL -> 0, denominator counts", led_n.denominator == 10 and led_n.verdict == "CONTESTED")

# ===========================================================================
print(f"\n=== {passes}/{passes + fails} ok ===")
if fails == 0:
    print("all green")
else:
    print(f"{fails} fail")
    sys.exit(1)