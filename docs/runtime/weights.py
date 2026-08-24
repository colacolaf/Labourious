"""Decision ledger — canonical agent signal weights for weighted synthesis.

Weights are RAW and intentionally NOT normalized to a fixed total (they need
not sum to 1, 85, or anything else). A flow wires whatever agents it wires;
the ledger normalizes against the *attached* set at collapse time:

    lean = sum(contribution) / sum(weight of attached agents with a completed read)

So a 2-agent graph and a 7-agent graph each get a lean on their own scale.
Attaching more voters dilutes each vote; attaching fewer makes each one count
more. This matches the app's custom-graph semantics and the TUI's per-flow
rosters: the roster is dynamic, the weights are not.

Roles:

  VOTERS (weighted)
    senior-analyst       30   lead thesis
    quant                25   valuation (price vs fair-value range)
    macro                10   regime modifier (no standalone verdict)
    technical            10   timing — reported on a SEPARATE horizon, never
                              blended into the thesis read
    flow-and-transcript  10   insider-flow signal (sparse but firm)

  NON-VOTERS (no weight, fixed rules)
    forensic-accounting     audit cap  — FLAGGED caps the *verdict* to CONTESTED
    devils-advocate         escalation — a sourced fragility caps *confidence*
                            at MIXED, it never flips the verdict alone
    sentiment               noise — weight 0, may only downgrade/annotate,
                            never contributes upward (see CONNECTORS-AUDIT)
    orchestrator / final-report — no vote (synthesis / memo layer)

Confidence -> multiplier: HIGH 1.0 · MODERATE_HIGH 0.75 · MIXED 0.5 · LOW 0.25
A missing confidence field contributes with multiplier 0.0.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

# --------------------------------------------------------------------------- #
# Canonical weights
# --------------------------------------------------------------------------- #

WEIGHTS: dict[str, int] = {
    "senior-analyst": 30,
    "quant": 25,
    "macro": 10,
    "technical": 10,
    "flow-and-transcript": 10,
}

NON_VOTING_ROLES: dict[str, str] = {
    "orchestrator": "synthesis layer — no vote",
    "forensic-accounting": "audit cap — FLAGGED caps the verdict to CONTESTED",
    "devils-advocate": "escalation — a sourced fragility caps confidence at MIXED",
    "sentiment": "noise — weight 0, may only downgrade or annotate",
    "final-report": "memo writer — no vote",
}

CONF_MULT: dict[str, float] = {
    "HIGH": 1.0,
    "MODERATE_HIGH": 0.75,
    "MIXED": 0.5,
    "LOW": 0.25,
}

# |lean| >= this -> a verdict; below it -> CONTESTED
LEAN_BAND: float = 0.60


# --------------------------------------------------------------------------- #
# Direction extraction (per agent's own envelope)
# --------------------------------------------------------------------------- #

def _senior_direction(env: dict[str, Any]) -> Optional[int]:
    bl = env.get("bottom_line")
    if not isinstance(bl, dict):
        thesis = env.get("thesis")
        bl = thesis.get("bottom_line") if isinstance(thesis, dict) else None
    if not isinstance(bl, dict):
        return None
    a = str(bl.get("action") or bl.get("direction") or "").upper()
    if a in ("BUY", "STRONG_BUY", "BULLISH", "ADD", "OVERWEIGHT", "ACCUMULATE"):
        return 1
    if a in ("SELL", "STRONG_SELL", "BEARISH", "REDUCE", "UNDERWEIGHT"):
        return -1
    if a in ("HOLD", "NEUTRAL", "FLAT"):
        return 0
    return None


def _quant_direction(env: dict[str, Any], price: Optional[float]) -> Optional[float]:
    if price is None:
        return None
    v = env.get("valuation")
    if not isinstance(v, dict):
        return None
    r = v.get("range")
    if not isinstance(r, dict):
        return None
    low, high = r.get("low"), r.get("high")
    if low is None or high is None:
        return None
    if price < low:
        return 1
    if price > high:
        return -1
    return 0  # price inside the model range -> informed neutral (keeps weight)


_GENERIC_DIRECTIONS = {
    "macro": ("macro_context", "regime_treatment", "FAVORABLE", "UNFAVORABLE", "NEUTRAL"),
    "technical": ("technical_analysis", "bias", "BULLISH", "BEARISH", "NEUTRAL"),
    "flow-and-transcript": ("flow_and_transcript", "insider", "BUY", "SELL", "FLAT"),
}


def direction_sign(agent_id: str, env: dict[str, Any], price: Optional[float] = None) -> Optional[float]:
    """Return +1 / 0 / -1, or None when the agent produced no directional read.

    None means \"no completed read\" (section absent, connector FAILED, or an
    explicit UNKNOWN): the agent falls out of the denominator entirely, so a
    data failure never dilutes the agents that actually read.
    """
    if agent_id == "senior-analyst":
        return _senior_direction(env)
    if agent_id == "quant":
        return _quant_direction(env, price)
    spec = _GENERIC_DIRECTIONS.get(agent_id)
    if spec is None:
        return None
    section, field, pos, neg, zero = spec
    sec = env.get(section)
    if not isinstance(sec, dict):
        return None
    if agent_id == "flow-and-transcript":
        inner = sec.get("insider")
        if not isinstance(inner, dict):
            return None
        val = inner.get("net")
    else:
        val = sec.get(field)
    if not isinstance(val, str):
        return None
    val = val.upper()
    if val == pos or val == "STRONG_" + pos:
        return 1
    if val == neg or val == "STRONG_" + neg:
        return -1
    if val == zero:
        return 0
    if val == "UNKNOWN":
        return None
    return None


# --------------------------------------------------------------------------- #
# Ledger computation
# --------------------------------------------------------------------------- #

@dataclass
class Contribution:
    agent_id: str
    weight: int
    confidence: Optional[str]
    direction: Optional[float]
    contribution: float


@dataclass
class Ledger:
    contributions: list[Contribution] = field(default_factory=list)
    numerator: float = 0.0
    denominator: int = 0
    lean: Optional[float] = None
    verdict: str = "NO_SIGNAL"           # pre-cap
    confidence: str = "LOW"              # aggregate confidence (post-cap)
    warnings: list[str] = field(default_factory=list)
    caps: list[str] = field(default_factory=list)

    @property
    def attached(self) -> list[str]:
        """Agents that produced a completed read (in the denominator)."""
        return [c.agent_id for c in self.contributions if c.direction is not None]

    @property
    def confirmed_verdict(self) -> str:
        """Verdict after audit caps. A forensic FLAGGED cap forces CONTESTED."""
        if self.verdict == "CONTESTED" or any("forensic" in c for c in self.caps):
            return "CONTESTED"
        return self.verdict


def compute_ledger(envelopes: dict[str, dict[str, Any]], price: Optional[float] = None) -> Ledger:
    """Collapse attached agent envelopes into a weighted lean.

    envelopes: {agent_id: envelope} (only attached agents need be present)
    price    : current market price (needed for quant's price-vs-range read)

    An agent contributes to the numerator AND denominator only when it
    produced a completed directional read. Absent / abstained / failed agents
    fall out of both.
    """
    ledger = Ledger()
    for agent_id, weight in WEIGHTS.items():
        env = envelopes.get(agent_id)
        if not isinstance(env, dict):
            continue  # not attached in this flow
        sign = direction_sign(agent_id, env, price)
        if sign is None:
            ledger.contributions.append(Contribution(agent_id, weight, env.get("confidence"), None, 0.0))
            continue
        mult = CONF_MULT.get(env.get("confidence"), 0.0)
        c = weight * mult * sign
        ledger.contributions.append(Contribution(agent_id, weight, env.get("confidence"), sign, c))
        ledger.numerator += c
        ledger.denominator += weight

    if ledger.denominator == 0:
        ledger.verdict = "NO_SIGNAL" \
            if ledger.verdict == "NO_SIGNAL" else ledger.verdict
        ledger.warnings.append("No attached agent produced a completed directional read.")
        return ledger

    ledger.lean = ledger.numerator / ledger.denominator
    ledger.verdict = (
        "LEAN_BULL" if ledger.lean >= LEAN_BAND
        else "LEAN_BEAR" if ledger.lean <= -LEAN_BAND
        else "CONTESTED"
    )
    ledger.confidence = _average_confidence(ledger.contributions)
    _apply_caps(ledger, envelopes)
    return ledger


def _average_confidence(contributions: list[Contribution]) -> str:
    """Weighted mean confidence multiplier across contributing agents."""
    total_w = sum(c.weight for c in contributions if c.direction is not None)
    if total_w == 0:
        return "LOW"
    avg = sum(
        CONF_MULT.get(c.confidence, 0.0) * c.weight
        for c in contributions if c.direction is not None
    ) / total_w
    if avg >= 0.8:
        return "HIGH"
    if avg >= 0.6:
        return "MODERATE_HIGH"
    if avg >= 0.4:
        return "MIXED"
    return "LOW"


def _apply_caps(ledger: Ledger, envelopes: dict[str, dict[str, Any]]) -> None:
    """Audit caps. Forensic FLAGGED caps the verdict; a sourced high-conviction
    devil's-advocate caps the aggregate confidence.

    NOTE: this applies only to the *aggregate* envelope (orchestrator /
    bridge-level). It does not mutate any agent's own envelope.
    """

    # Forensic-accounting: the verdict cannot stand if earnings quality is
    # in material doubt, regardless of what the other votes say.
    fenv = envelopes.get("forensic-accounting")
    if isinstance(fenv, dict):
        verdict = fenv.get("verdict")
        if isinstance(verdict, str) and "FLAG" in verdict.upper():
            ledger.caps.append("forensic-accounting FLAGGED — verdict capped to CONTESTED")

    # Devils-advocate: a sourced, high-conviction fragility caps the aggregate
    # confidence. It never flips the verdict — it forces the memo to say MIXED.
    denv = envelopes.get("devils-advocate")
    if isinstance(denv, dict):
        frag = denv.get("fragile_assumption")
        base_rates = denv.get("base_rates") or []
        sourced = isinstance(frag, str) and len(frag.strip()) > 0 and len(base_rates) > 0
        if sourced and denv.get("confidence") in ("HIGH", "MODERATE_HIGH"):
            ledger.confidence = "MIXED"
            ledger.caps.append("devils-advocate raised a sourced fragility — aggregate confidence capped at MIXED")

    # Sentiment never contributes. It can only annotate (warn) when it is
    # STRONG and *opposes* the lean — proving it still carries weight 0.
    senv = envelopes.get("sentiment")
    if isinstance(senv, dict):
        s = senv.get("sentiment")
        if isinstance(s, dict) and s.get("signal_tier") == "STRONG" and ledger.lean is not None:
            bull_share = s.get("bull_share")
            if isinstance(bull_share, (int, float)):
                opposes = (ledger.lean > 0 and bull_share < 0.5) or (ledger.lean < 0 and bull_share > 0.5)
                if opposes:
                    ledger.warnings.append("sentiment opposes the lean — noted, no weight applied")