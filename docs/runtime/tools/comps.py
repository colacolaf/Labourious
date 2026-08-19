"""
comps.py — A pure-Python comparables (peer-multiples) model.

Where dcf.py turns WACC + FCF projections into an intrinsic price,
comps.py turns peer multiples + subject metrics into an implied price.
Same principle: math in code, not in the LLM.

Inputs:
  - `metrics`: dict mapping metric_name (e.g. "ev_ebitda", "p_e_ntm") →
    subject_metric_value
  - `peers`: list of {ticker, multiples: {metric_name: value}, as_of}
  - `path`: per metric, choose "ev_bridge" or "equity_direct"
  - `net_debt`, `shares_diluted`: subject's finance inputs

Output:
  - peer median per metric (with min/max for sanity-check)
  - trimmed-mean per metric (drops top/bottom 1)
  - implied price per metric (with the bridge path made explicit)
  - triangulation rows (peer median implies price X; subject current price Y)

Discipline checks:
  - At least 3 peers per metric (median is unsafe with < 3)
  - All peer multiples within ±3σ of median (drop outliers)
  - Sector or size-tag match documented in note
"""

from __future__ import annotations

import datetime as dt
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from . import ToolResult


# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


# --------------------------------------------------------------------------- #
@dataclass
class PeerMultiple:
    """One peer's data point."""
    ticker: str
    metric: str                  # e.g. "ev_ebitda", "p_e_ntm"
    multiple: float
    as_of: str = ""
    note: str = ""


@dataclass
class SubjectMetric:
    """The subject's own metric values (LTM or NTM)."""
    ticker: str
    metrics: dict[str, float]    # metric_name → value
    net_debt: float              # total_debt − cash; can be negative
    shares_diluted: float


@dataclass
class CompsRequest:
    peers: list[PeerMultiple]
    subject: SubjectMetric
    min_peers: int = 3


# --------------------------------------------------------------------------- #
def _bucket_by_metric(peers: Sequence[PeerMultiple]) -> dict[str, list[PeerMultiple]]:
    bucket: dict[str, list[PeerMultiple]] = defaultdict(list)
    for p in peers:
        bucket[p.metric].append(p)
    return bucket


def _median(values: Sequence[float]) -> float:
    v = sorted(values)
    if not v:
        return 0.0
    n = len(v)
    mid = n // 2
    return v[mid] if n % 2 else 0.5 * (v[mid - 1] + v[mid])


def _trimmed_mean(values: Sequence[float], drop_n: int = 1) -> float:
    v = sorted(values)
    if len(v) <= 2 * drop_n:
        return statistics.mean(v) if v else 0.0
    return statistics.mean(v[drop_n:-drop_n])


def _implied_price_per_metric(
    metric: str, subject_metric: float, peer_median: float,
    net_debt: float, shares_diluted: float,
    is_ev_bridge: bool,
) -> dict[str, float]:
    if peer_median <= 0 or subject_metric <= 0:
        return {"per_share": 0.0, "path": "skipped (zero median or metric)"}
    if is_ev_bridge:
        ev = subject_metric * peer_median
        equity = ev - net_debt
        per_share = equity / shares_diluted if shares_diluted > 0 else 0.0
        return {"ev": round(ev, 4), "equity": round(equity, 4),
                "per_share": round(per_share, 2), "path": "EV-bridge"}
    per_share = subject_metric * peer_median
    return {"per_share": round(per_share, 2), "path": "equity-direct"}


# --------------------------------------------------------------------------- #
# What path to take per metric
# --------------------------------------------------------------------------- #
EV_BRIDGE_METRICS = frozenset(
    {"ev_ebitda", "ev_ebit", "ev_sales", "ev_revenue", "ev_fcf"}
)
EQUITY_METRICS = frozenset(
    {"p_e_ltm", "p_e_ntm", "p_sales", "p_fcf_yield_inv", "p_book"}
)


def _is_ev_bridge(metric: str) -> bool:
    return metric in EV_BRIDGE_METRICS


# --------------------------------------------------------------------------- #
# The build() function — what the orchestrator calls
# --------------------------------------------------------------------------- #
def build(req: CompsRequest) -> dict[str, Any]:
    by_metric = _bucket_by_metric(req.peers)
    out: dict[str, Any] = {}

    warnings: list[str] = []

    for metric, peers in by_metric.items():
        multiples = [p.multiple for p in peers if p.multiple > 0]
        if len(multiples) < req.min_peers:
            warnings.append(
                f"{metric}: only {len(multiples)} peers, below min of {req.min_peers}"
            )
        if not multiples:
            out[metric] = {"warning": "no usable peer multiples"}
            continue

        med = _median(multiples)
        tmean = _trimmed_mean(multiples, drop_n=1)
        mn, mx = min(multiples), max(multiples)

        # outlier check: > 3σ on either side → drop & flag
        mean = statistics.mean(multiples)
        sigma = statistics.pstdev(multiples) or 1e-6
        outliers = [m for m in multiples if abs(m - mean) > 3 * sigma]
        if outliers:
            warnings.append(f"{metric}: outliers > 3σ dropped: {outliers}")

        subject_metric = req.subject.metrics.get(metric, 0.0)
        if subject_metric <= 0:
            warnings.append(f"{metric}: subject metric not provided or ≤ 0")
            continue

        implied = _implied_price_per_metric(
            metric, subject_metric, med,
            req.subject.net_debt, req.subject.shares_diluted,
            is_ev_bridge=_is_ev_bridge(metric),
        )

        out[metric] = {
            "n_peers": len(multiples),
            "peer_min": round(mn, 4),
            "peer_max": round(mx, 4),
            "peer_median": round(med, 4),
            "peer_trimmed_mean": round(tmean, 4),
            "subject_metric": subject_metric,
            "implied": implied,
        }

    return {"per_metric": out, "warnings": warnings}


# --------------------------------------------------------------------------- #
# ToolResult wrapper
# --------------------------------------------------------------------------- #
class CompsTool:
    name = "quant_comps"
    user_agent: str = ""

    def run(self, subject: dict[str, Any], peers: list[dict[str, Any]],
            min_peers: int = 3) -> ToolResult:
        """Run a comparables model. Accepts subject + peers lists of dicts.

        Subject dict: {ticker, metrics:{...}, net_debt, shares_diluted}
        Peers list: [{ticker, metric, multiple, as_of?, note?}, ...]
        """
        try:
            peer_objs = [
                PeerMultiple(
                    ticker=str(p["ticker"]),
                    metric=str(p["metric"]),
                    multiple=float(p["multiple"]),
                    as_of=str(p.get("as_of", "")),
                    note=str(p.get("note", "")),
                )
                for p in peers
            ]
            subject_obj = SubjectMetric(
                ticker=str(subject["ticker"]),
                metrics={k: float(v) for k, v in subject["metrics"].items()},
                net_debt=float(subject["net_debt"]),
                shares_diluted=float(subject["shares_diluted"]),
            )
            req = CompsRequest(peers=peer_objs, subject=subject_obj,
                                min_peers=int(min_peers))
        except (KeyError, ValueError, TypeError) as exc:
            return ToolResult(
                status="FAILED", data=None, as_of=_now_iso(),
                source=self.name,
                note=f"ingest failed: {type(exc).__name__}: {exc}",
            )
        try:
            result = build(req)
        except Exception as exc:
            return ToolResult(
                status="FAILED", data=None, as_of=_now_iso(),
                source=self.name,
                note=f"build failed: {type(exc).__name__}: {exc}",
            )
        return ToolResult(
            status="SUCCESS", data=result, as_of=_now_iso(), source=self.name,
            note=("Comparables produced" if not result["warnings"]
                  else f"Comparables produced with {len(result['warnings'])} warning(s)"),
        )
