"""
comparator.py — A pure-Python comparator for multi-ticker rankings (f2).

This is the aggregation layer for the "compare N tickers" flow. Per-ticker
LLM work (senior-analyst, forensic, devils-advocate) runs in parallel
upstream; this module collapses their outputs into a ranked pick with a
provable audit trail.

What it does, end-to-end:
  1. Parse a rubric (free-text or list-of-dimensions) into a normalized
     weights vector over the 6 standard dimensions.
  2. Score each ticker on each dimension (qualitative lookup + cohort-
     normalized quantitative where available).
  3. Weighted-sum to a single ranked score per ticker.
  4. Perturb weights ±10% per dimension. Each perturbation recomputes
     the rank. The set of "top-3 flips" is the sensitivity signal.
  5. Confidence: HIGH if no top-3 flip under any single-dimension
     perturbation; LOW if the top-3 changes on every dimension.

Discipline from canon (Wikipedia "Valuation using multiples"):
  - Adjustments, not raw medians. We use cohort-normalized scoring so a
    ticker that is "the most expensive in the cohort" still gets a 0; a
    ticker that is "the cheapest" gets 1.
  - Per-dimension winners must justify the rank with 1 line of evidence.
  - Sensitivity must show robust pick OR explicit fragility.

Discipline from canon (Anthropic multi-agent paper):
  - Each per-ticker agent ran in its own context. This module aggregates;
    it does NOT re-derive qualitative claims.
"""

from __future__ import annotations

import datetime as dt
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from . import ToolResult


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# --------------------------------------------------------------------------- #
# Rubric
# --------------------------------------------------------------------------- #
# Six standard dimensions. The mapping is exhaustive for the comparator's
# MVP — adding a new dimension is a one-line edit here + matching enrich.
SUPPORTED_DIMENSIONS = (
    "valuation",     # P/E vs cohort, DCF vs market, multiple-implied
    "growth",        # revenue/EPS growth consensus
    "quality",       # ROIC, margin trajectory, moat signals
    "leverage",      # net debt / EBITDA, interest coverage
    "momentum",      # 6/12-month price return, revision momentum
    "sentiment",     # broker upgrades/downgrades, short interest, news
)


# Keywords → dimension weights. Tuned to be additive (each keyword adds),
# not overriding. The final weight vector is renormalized.
RUBRIC_KEYWORDS: dict[str, dict[str, float]] = {
    "valuation": {
        "cheap": 0.30, "value": 0.30, "undervalued": 0.30,
        "low pe": 0.30, "discount": 0.30, "below intrinsic": 0.30,
    },
    "growth": {
        "growth": 0.30, "fast growing": 0.25, "accelerating": 0.30,
        "high growth": 0.30, "expansion": 0.25,
    },
    "quality": {
        "quality": 0.30, "moat": 0.30, "best-in-class": 0.30,
        "operational": 0.20, "durable": 0.30, "high roic": 0.30,
    },
    "leverage": {
        "low leverage": 0.30, "de-leveraged": 0.30, "low debt": 0.30,
        "balance sheet strength": 0.30,
    },
    "momentum": {
        "momentum": 0.30, "trending": 0.30, "outperform": 0.25,
        "winning": 0.30, "price strength": 0.25,
    },
    "sentiment": {
        "sentiment": 0.30, "consensus": 0.20, "wall street": 0.20,
        "insider": 0.25, "analyst": 0.20,
    },
}


def parse_rubric(rubric: str | Sequence[str] | None) -> dict[str, float]:
    """Parse a rubric into a weights vector.

    Accepts:
      - None / "" / balanced → returns equal weights
      - string of comma-separated keys, each optionally prefixed with '+' or '-'
        (e.g. "+growth, -leverage"). '-' subtracts from that dimension's weight.
      - list of plain keys (e.g. ["growth", "valuation"])
      - dict (treated as already-balanced weights)

    Renormalizes so weights sum to 1.0. A dimension with no signal at all
    gets 1/(N) of the weight (the balanced default).
    """
    base = {d: 1.0 / len(SUPPORTED_DIMENSIONS) for d in SUPPORTED_DIMENSIONS}

    if rubric is None or (isinstance(rubric, str) and not rubric.strip()):
        return base
    if isinstance(rubric, dict):
        # validate keys
        for k in rubric.keys():
            if k not in SUPPORTED_DIMENSIONS:
                raise ValueError(f"rubric key '{k}' not in {SUPPORTED_DIMENSIONS}")
        out = base.copy()
        out.update(rubric)
        total = sum(out.values()) or 1.0
        return {k: v / total for k, v in out.items()}

    if isinstance(rubric, str):
        tokens = [t.strip() for t in rubric.split(",") if t.strip()]
    else:
        tokens = list(rubric)

    weight_overrides: dict[str, float] = {d: 0.0 for d in SUPPORTED_DIMENSIONS}
    for tok in tokens:
        sign = 1
        clean = tok.lower().lstrip("+")
        if clean.startswith("-"):
            sign = -1
            clean = clean.lstrip("-").strip()
        # match against KNOWN keywords — longest first to avoid partial matches
        matched = False
        for dim, kw in sorted(RUBRIC_KEYWORDS.items(), key=lambda kv: -max(len(k) for k in kv[1])):
            for keyword, strength in sorted(kw.items(), key=lambda kv: -len(kv[0])):
                if keyword in clean or clean in keyword:
                    weight_overrides[dim] += sign * strength
                    matched = True
                    break
            if matched:
                break
        if not matched:
            # bare dimension name
            if clean in SUPPORTED_DIMENSIONS:
                weight_overrides[clean] += sign * 0.30
            # else: silently ignore unknown tokens; f2 callers can be noisy

    # Merge overrides on top of base.
    out = {d: base[d] + weight_overrides.get(d, 0.0) for d in SUPPORTED_DIMENSIONS}

    # Negative weights → 0 (don't add them in the inverse direction)
    out = {d: max(v, 0.0) for d, v in out.items()}

    # Renormalize
    total = sum(out.values()) or 1.0
    return {d: v / total for d, v in out.items()}


# --------------------------------------------------------------------------- #
# Qualitative dimension scores
# --------------------------------------------------------------------------- #
QUALITATIVE_SCALE: dict[str, dict[str, float]] = {
    "valuation":     {"cheap": 1.0, "fair": 0.6, "rich": 0.2, "stretched": 0.0, "unsupported": 0.5},
    "growth":        {"accelerating": 1.0, "steady": 0.6, "decelerating": 0.3, "shrinking": 0.0, "unknown": 0.5},
    "quality":       {"high": 1.0, "medium": 0.6, "low": 0.2, "unknown": 0.5},
    "leverage":      {"low": 1.0, "moderate": 0.6, "high": 0.3, "distressed": 0.0, "unknown": 0.5},
    "momentum":      {"positive": 1.0, "neutral": 0.5, "negative": 0.1},
    "sentiment":     {"bullish": 1.0, "neutral": 0.5, "bearish": 0.1},
}


DIRECTION_SCORE: dict[str, float] = {"BUY": 1.0, "HOLD": 0.5, "SELL": 0.0, "ABSTAIN": 0.5,
                                       "NOT_FOUND": 0.5}


# --------------------------------------------------------------------------- #
# Per-ticker input
# --------------------------------------------------------------------------- #
@dataclass
class TickerInput:
    ticker: str
    # Senior-analyst run output (read-only by comparator)
    direction: str = "ABSTAIN"               # BUY/HOLD/SELL/ABSTAIN
    conviction: int = 3                       # 1-5
    thesis_one_sentence: str = ""
    fragile_assumption: str = ""
    citation_count: int = 0
    # Qualitative dimensions (from senior-analyst's `dimensions` block)
    dimensions: dict[str, str] = field(default_factory=dict)
    # Quantitative measurements (best-effort from senior-analyst + forensic)
    quant: dict[str, float] = field(default_factory=dict)
    # Citations attached
    citations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ComparatorRequest:
    rubric: str | list[str] | dict[str, float] | None
    tickers: list[TickerInput]
    sensitivity_pct: float = 0.10


# --------------------------------------------------------------------------- #
# Cohort normalization (for quantitative fields)
# --------------------------------------------------------------------------- #
def _cohort_normalize(values: list[float], lower_is_better: bool = False) -> list[float]:
    """Min-max normalize a list of floats.

    Returns scores in [0, 1] (best = 1.0, worst = 0.0). If `lower_is_better`
    is True (e.g., for P/E, leverage), the smallest value gets 1.0.
    Equal values all get 0.5.
    """
    if not values:
        return []
    mn, mx = min(values), max(values)
    if mn == mx:
        return [0.5] * len(values)
    out = []
    for v in values:
        s = (v - mn) / (mx - mn)
        if lower_is_better:
            s = 1.0 - s
        out.append(_clamp(s))
    return out


# --------------------------------------------------------------------------- #
# Per-ticker scoring (each dimension -> [0, 1])
# --------------------------------------------------------------------------- #
def _score_qualitative(dim: str, value: str) -> float:
    return QUALITATIVE_SCALE.get(dim, {}).get(value.lower(), 0.5)


@dataclass
class ScoredTicker:
    ticker: TickerInput
    dimension_scores: dict[str, float]   # each [0,1]
    final_score: float                   # weighted sum [0,1]
    per_dim_winner: bool                  # is this the top-2 ticker for this dimension?
    rank: int = 0


def score_each_ticker(
    tickers: list[TickerInput], weights: dict[str, float],
) -> tuple[list[ScoredTicker], dict[str, list[str]]]:
    """Compute per-dimension scores + final weighted score + dimension leaders.

    Returns the per-ticker scoring list AND a `leaders` map listing the
    tickers leading each dimension (used to build the winner-justification
    section of the memo).
    """
    # 1. Quantitative cohort normalization (where values are present).
    # Whitelist of quant fields per dimension.
    QUANT_BY_DIM: dict[str, tuple[str, bool]] = {
        "valuation": ("pe_ntm", True),                  # lower P/E is better
        "growth": ("growth_consensus_pct", False),      # higher growth is better
        "quality": ("roic_pct", False),                  # higher ROIC is better
        "leverage": ("leverage_ratio", True),            # lower leverage is better
        "momentum": ("return_6m_pct", False),            # higher return is better
        "sentiment": ("analyst_rating", False),          # 1-5; higher is more bullish
    }

    n = len(tickers)
    # Gather quantitative measures per dim (skipped if none).
    cohort_dim_scores: dict[str, list[float]] = defaultdict(lambda: [0.5] * n)
    for dim, (field_name, lower_is_better) in QUANT_BY_DIM.items():
        raw = [t.quant.get(field_name) for t in tickers]
        # Preserve positions of missing values; only normalize the present ones.
        present_idx = [i for i, v in enumerate(raw) if v is not None]
        present_vals = [raw[i] for i in present_idx]
        if present_vals:
            normalized = _cohort_normalize(present_vals, lower_is_better=lower_is_better)
            for idx, s in zip(present_idx, normalized):
                cohort_dim_scores[dim][idx] = s

    # Build per-ticker dimension scores.
    scored: list[ScoredTicker] = []
    per_dim_scores: dict[str, list[float]] = defaultdict(list)

    for i, t in enumerate(tickers):
        scores: dict[str, float] = {}
        for dim in SUPPORTED_DIMENSIONS:
            qual = _score_qualitative(dim, t.dimensions.get(dim, "unknown"))
            quant = cohort_dim_scores.get(dim, [0.5] * n)[i] if i < n else 0.5
            # If quant wasn't provided, qualitative-only (no blend penalty).
            if dim in t.quant or any(t.quant.get(QUANT_BY_DIM.get(dim, ("",))[0]) is not None
                                     for t in tickers):
                # 70/30 blend when quant is at least partially available.
                scores[dim] = _clamp(0.7 * quant + 0.3 * qual, 0.0, 1.0)
            else:
                scores[dim] = qual
        # Augment with conviction as a 7th implicit "conviction" axis.
        # We don't force it into the rubric; we mix it as floor.
        conviction_norm = _clamp((t.conviction - 1) / 4.0)   # 1-5 → 0-1

        # Final weighted sum.
        final = sum(weights[d] * scores[d] for d in SUPPORTED_DIMENSIONS)
        # Apply a small conviction lift so high-conviction bounces beat.
        final = _clamp(0.9 * final + 0.10 * conviction_norm, 0.0, 1.0)

        st = ScoredTicker(ticker=t, dimension_scores=scores,
                            final_score=final, per_dim_winner=False)
        scored.append(st)
        for d in SUPPORTED_DIMENSIONS:
            per_dim_scores[d].append(scores[d])

    # Identify leaders (top-2 per dimension).
    leaders: dict[str, list[str]] = {}
    for d in SUPPORTED_DIMENSIONS:
        ordered = sorted(enumerate(per_dim_scores[d]),
                          key=lambda kv: -kv[1])
        top2_idx = [i for i, _ in ordered[:2]]
        leaders[d] = [tickers[i].ticker for i in top2_idx]
        for i in top2_idx:
            scored[i].per_dim_winner = True

    # Rank.
    ranked = sorted(enumerate(scored), key=lambda kv: -kv[1].final_score)
    for new_rank, (orig_idx, st) in enumerate(ranked, start=1):
        scored[orig_idx].rank = new_rank
    return scored, leaders


# --------------------------------------------------------------------------- #
# Sensitivity (±pct on each weight in turn; rest renormalize)
# --------------------------------------------------------------------------- #
def sensitivity_perturbation(
    tickers: list[TickerInput],
    base_weights: dict[str, float],
    pct: float = 0.10,
    top_n: int = 3,
) -> dict[str, Any]:
    """For each dimension, perturb its weight by ±pct, renormalize, rerank.

    Returns a dict describing:
      - per_dim_picks: {dim: {dim+ : winner, dim- : winner}}
      - flips_top_n: number of dimensions where perturbing flips the
        top-N pic
      - robust_pick: ticker(s) that win the top-N across ALL perturbations
    """
    base_scored, _ = score_each_ticker(tickers, base_weights)
    base_top_n = [s.ticker.ticker for s in sorted(base_scored, key=lambda s: s.rank)[:top_n]]

    per_dim_picks: dict[str, dict[str, str]] = {}
    flips_count = 0
    for dim_to_perturb in SUPPORTED_DIMENSIONS:
        for sign in ("plus", "minus"):
            new_w = base_weights.copy()
            new_w[dim_to_perturb] = max(0.0, new_w[dim_to_perturb] * (1.0 + (pct if sign == "plus" else -pct)))
            total = sum(new_w.values()) or 1.0
            new_w = {k: v / total for k, v in new_w.items()}
            new_scored, _ = score_each_ticker(tickers, new_w)
            new_top = [s.ticker.ticker for s in sorted(new_scored, key=lambda s: s.rank)[:top_n]]
            per_dim_picks.setdefault(dim_to_perturb, {})[sign] = new_top[0]
            # Compare top-1 across perturbations.
            if new_top[0] != base_top_n[0]:
                flips_count += 1

    return {
        "per_dim_picks": per_dim_picks,
        "flips_total_dim1": flips_count,
        "max_dim_to_flip_top1": flips_count,
        "robust_top1": sum(1 for dim in per_dim_picks.values()
                           if dim.get("plus") == base_top_n[0] and dim.get("minus") == base_top_n[0])
        / max(1, len(per_dim_picks)),
        "base_top_n": base_top_n,
    }


# --------------------------------------------------------------------------- #
# Confidence
# --------------------------------------------------------------------------- #
def confidence(sensitivity: dict[str, Any]) -> str:
    """HIGH/MEDIUM/LOW based on top-1 robustness across perturbations."""
    flips = sensitivity["flips_total_dim1"]
    if flips == 0:
        return "HIGH"
    if flips <= 2:
        return "MEDIUM"
    return "LOW"


# --------------------------------------------------------------------------- #
# Build — what the orchestrator calls
# --------------------------------------------------------------------------- #
def build(request: ComparatorRequest) -> dict[str, Any]:
    weights = parse_rubric(request.rubric)
    scored, leaders = score_each_ticker(request.tickers, weights)
    sensitivity = sensitivity_perturbation(request.tickers, weights,
                                            pct=request.sensitivity_pct, top_n=3)
    conf = confidence(sensitivity)

    # Sort by rank for the deliverables list.
    ranked_scored = sorted(scored, key=lambda s: s.rank)

    return {
        "weights": weights,
        "rubric_parsed_as": (request.rubric if isinstance(request.rubric, str)
                              else ("balanced" if request.rubric is None
                                    else f"{len(request.rubric)}-token rubric")),
        "per_ticker": [
            {
                "ticker": s.ticker.ticker,
                "rank": s.rank,
                "final_score": round(s.final_score, 4),
                "dimension_scores": {d: round(s.dimension_scores[d], 4)
                                       for d in SUPPORTED_DIMENSIONS},
                "direction": s.ticker.direction,
                "conviction": s.ticker.conviction,
                "thesis_one_sentence": s.ticker.thesis_one_sentence,
                "fragile_assumption": s.ticker.fragile_assumption,
                "key_citations": s.ticker.citations[:3],
                "per_dim_winner_count": sum(1 for d in SUPPORTED_DIMENSIONS
                                              if s.ticker.ticker in leaders[d]),
            }
            for s in ranked_scored
        ],
        "dimension_leaders": leaders,
        "sensitivity": sensitivity,
        "confidence": conf,
        "warnings": [],
    }


# --------------------------------------------------------------------------- #
# ToolResult wrapper
# --------------------------------------------------------------------------- #
class ComparatorTool:
    name = "quant_comparator"
    user_agent: str = ""

    def run(self, tickers: list[dict[str, Any]],
            rubric: str | list[str] | dict[str, float] | None = None,
            sensitivity_pct: float = 0.10) -> ToolResult:
        """Run the comparator. Args are flat kwargs (mapped via call_tool).

        tickers: list of per-ticker dicts (ticker, dimensions, quant, etc.)
        rubric: free-text, list of tokens, or explicit dict
        sensitivity_pct: weight perturbation range for robustness check
        """
        try:
            ticker_objs = [
                TickerInput(
                    ticker=str(t["ticker"]),
                    direction=str(t.get("direction", "ABSTAIN")),
                    conviction=int(t.get("conviction", 3)),
                    thesis_one_sentence=str(t.get("thesis_one_sentence", "")),
                    fragile_assumption=str(t.get("fragile_assumption", "")),
                    citation_count=int(t.get("citation_count", 0)),
                    dimensions={k: str(v) for k, v in t.get("dimensions", {}).items()},
                    quant={k: float(v) for k, v in t.get("quant", {}).items()},
                    citations=list(t.get("citations", [])),
                )
                for t in tickers
            ]
            req = ComparatorRequest(
                rubric=rubric,
                tickers=ticker_objs,
                sensitivity_pct=float(sensitivity_pct),
            )
        except (KeyError, ValueError, TypeError) as exc:
            return ToolResult(
                status="FAILED", data=None, as_of=_now_iso(), source=self.name,
                note=f"ingest failed: {type(exc).__name__}: {exc}",
            )
        try:
            result = build(req)
        except Exception as exc:
            return ToolResult(
                status="FAILED", data=None, as_of=_now_iso(), source=self.name,
                note=f"build failed: {type(exc).__name__}: {exc}",
            )
        return ToolResult(
            status="SUCCESS", data=result, as_of=_now_iso(), source=self.name,
            note=(f"{len(tickers)}-ticker comparison complete; "
                  f"top pick = {result['per_ticker'][0]['ticker']}; "
                  f"confidence={result['confidence']}")
        )
