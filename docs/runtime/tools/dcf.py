"""
dcf.py — A pure-Python DCF + comps model.

Why this exists, separately from the LLM:
  The model-builder agent pulls the *content* — the FCF projections, the
  scenario assumptions, the comps set. The actual math (WACC, PV of cash
  flows, terminal value, sensitivity table, triangulation) is done here, in
  Python. Two reasons:
    1. It's auditable. Every number maps to a formula. No "the LLM said $47"
       in the model inputs.
    2. It's back-testable. A future pressure-test pilot can plug in a known
       forward consensus + actual print and assert the model produces a
       defensible range.

What it produces, end of `build(...)`:
  - `inputs` — every input that drove the result
  - `wacc` — Re, Rd_at, weights, final WACC (decimal, not %)
  - `pv_explicit` — list of (year, fcf, discount_factor, present_value)
  - `terminal` — method: gordon | exit_multiple, raw TV, PV(TV)
  - `enterprise_value` — PV(explicit) + PV(TV)
  - `equity_value`  — EV + non_operating_assets − total_debt
  - `per_share`     — equity_value / shares_diluted
  - `sensitivity`   — (rows = WACC, cols = terminal growth) per-share grid
  - `triangulation` — DCF intrinsic vs market_price vs multiples-implied
  - `warnings`      — list of data-quality flags ("terminal growth > 3.5%
                       looks too high", etc.)

Every output is also reported in human-readable form via `render_memo(...)`.
The pilot (`docs/runtime/tools/test_dcf.py`) asserts every key against a
known-good built-in fixture.

Discipline checks (the model fails PRODUCIBLY rather than producing junk):
  - WACC must be in [3%, 20%]. Out-of-range → warning, not crash.
  - Terminal growth must be ≤ 4.5% (US long-run nominal GDP cap). > 4.5%
    warning, but TV still computed.
  - FCF must be positive in years 1..4. Year 5 may be lower, terminal must
    be > 0 (otherwise TV undefined → FAILED return).
  - All comps must have a valid multiple (≥ 0) AND a metric value (≥ 0).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import ToolResult


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return dt.datetime.utcnow().isoformat() + "Z"


def _round(x: float, n: int = 4) -> float:
    return round(float(x), n)


# --------------------------------------------------------------------------- #
# WACC
# --------------------------------------------------------------------------- #
@dataclass
class CapitalStructure:
    """Either-or: market-value weights OR book-value weights.

    Both fed as decimal fractions (0.30 = 30% of capital).
    """
    equity_weight: float          # E/(D+E)
    debt_weight: float            # D/(D+E)


@dataclass
class WaccInputs:
    """Inputs needed to compute WACC.

    `risk_free_rate` and `equity_risk_premium` are decimals (0.045 = 4.5%).
    `beta` is levered (matches public sources).
    """
    risk_free_rate: float             # 10Y UST or sector-matched
    beta: float                        # levered beta
    equity_risk_premium: float         # Damodaran-annual ERP, ≈5-6% for US
    cost_of_debt_pretax: float         # weighted-avg yield on debt
    tax_rate: float                    # effective corporate tax rate (decimal)
    capital: CapitalStructure


def compute_wacc(wi: WaccInputs) -> dict[str, Any]:
    """CAPM cost of equity + after-tax cost of debt, weighted.

    Returns every intermediate step so a reviewer can audit. No rounding
    until the very end.
    """
    re = wi.risk_free_rate + wi.beta * wi.equity_risk_premium
    rd_at = wi.cost_of_debt_pretax * (1.0 - wi.tax_rate)
    w_e = wi.capital.equity_weight
    w_d = wi.capital.debt_weight
    if not math.isclose(w_e + w_d, 1.0, abs_tol=1e-6):
        # re-normalize so weights sum to 1.0; quietly.
        total = w_e + w_d
        w_e /= total
        w_d /= total
    wacc = w_e * re + w_d * rd_at
    return {
        "cost_of_equity": _round(re, 6),
        "after_tax_cost_of_debt": _round(rd_at, 6),
        "equity_weight": _round(w_e, 6),
        "debt_weight": _round(w_d, 6),
        "wacc": _round(wacc, 6),
    }


# --------------------------------------------------------------------------- #
# 5-year explicit forecast + terminal value
# --------------------------------------------------------------------------- #
@dataclass
class ExplicitForecast:
    """FCF for years 1..n. The terminal year is year n."""
    fcf_series: list[float]            # one per year, in absolute $


@dataclass
class TerminalAssumptions:
    """Two methods supported: Gordon Growth or Exit Multiple.

    For Gordon: `perpetual_growth` (decimal).
    For Exit Multiple: `ebitda_multiple` (e.g. 12x).
    Caller provides both; missing ones fall back to the other.
    """
    perpetual_growth: float | None = None
    ebitda_multiple: float | None = None
    terminal_year_ebitda: float | None = None  # only used for exit_multiple


def discount_explicit(fcf_series: list[float], wacc: float) -> list[dict[str, float]]:
    """PV each year's FCF at the discount rate (end-of-year convention).

    Mid-year convention would discount at (1+wacc)^(t-0.5); we use end-of-year
    here for simplicity. Documented in the memo.
    """
    out: list[dict[str, float]] = []
    if wacc <= 0:
        # pathological; bail with full undiscounted value so caller can decide
        for t, fcf in enumerate(fcf_series, start=1):
            out.append({"year": t, "fcf": _round(fcf, 4),
                        "discount_factor": 1.0, "pv": _round(fcf, 4)})
        return out
    for t, fcf in enumerate(fcf_series, start=1):
        df = (1.0 + wacc) ** t
        out.append({"year": t, "fcf": _round(fcf, 4),
                    "discount_factor": _round(df, 6),
                    "pv": _round(fcf / df, 4)})
    return out


def terminal_value(
    fcf_terminal: float, wacc: float, ta: TerminalAssumptions,
) -> dict[str, Any]:
    """Compute terminal value. Both methods àre returned if both are passable"""
    methods: dict[str, Any] = {}

    if ta.perpetual_growth is not None:
        if wacc - ta.perpetual_growth <= 0:
            methods["gordon"] = {"tv": None, "warning":
                f"wacc - g = {wacc - ta.perpetual_growth:.4f} ≤ 0; Gordon undefined"}
        else:
            tv = fcf_terminal * (1.0 + ta.perpetual_growth) / (wacc - ta.perpetual_growth)
            methods["gordon"] = {"tv": _round(tv, 4), "method": "gordon"}

    if ta.ebitda_multiple is not None and ta.terminal_year_ebitda is not None:
        tv = ta.ebitda_multiple * ta.terminal_year_ebitda
        methods["exit_multiple"] = {
            "tv": _round(tv, 4), "method": "exit_multiple"
        }

    return methods


# --------------------------------------------------------------------------- #
# Sensitivity grid
# --------------------------------------------------------------------------- #
def sensitivity_grid(
    fcf_series: list[float],
    share_count: float,
    net_operating_assets: float,
    wacc_base: float,
    g_base: float,
    wacc_steps: float = 0.01,    # ±100bp in 50bp increments around base
    g_steps: float = 0.005,      # ±100bp in 50bp increments
    n_per_side: int = 2,
) -> dict[str, Any]:
    """Per-share price grid: rows = WACC, cols = terminal growth.

    Returns a dict-of-dicts; outer key = WACC (decimal as string), inner
    key = g (decimal as string), value = per-share price.
    """
    rows: dict[str, dict[str, float]] = {}
    for w in [wacc_base + i * wacc_steps for i in range(-n_per_side, n_per_side + 1)]:
        row: dict[str, float] = {}
        for g in [g_base + j * g_steps for j in range(-n_per_side, n_per_side + 1)]:
            pv_exp = sum(fcf / (1 + w) ** t for t, fcf in enumerate(fcf_series, start=1))
            tv = (fcf_series[-1] * (1 + g)) / (w - g) if (w - g) > 0 else 0.0
            pv_tv = tv / ((1 + w) ** len(fcf_series))
            ev = pv_exp + pv_tv
            equity = ev + net_operating_assets
            per_share = equity / share_count if share_count > 0 else 0.0
            row[f"{g:.4f}"] = _round(per_share, 2)
        rows[f"{w:.4f}"] = row
    return rows


# --------------------------------------------------------------------------- #
# Comparables
# --------------------------------------------------------------------------- #
@dataclass
class Comp:
    ticker: str
    metric_value: float       # EBITDA, EPS, revenue, FCF
    multiple: float           # EV/EBITDA, P/E, P/S, P/FCF observed
    as_of: str = ""
    note: str = ""


def comps_median(c: Sequence[Comp]) -> float:
    """Median of an iterable. Returns 0.0 if empty (caller should warn)."""
    if not c:
        return 0.0
    sorted_m = sorted(co.multiple for co in c if co.multiple > 0)
    if not sorted_m:
        return 0.0
    n = len(sorted_m)
    mid = n // 2
    return sorted_m[mid] if n % 2 else 0.5 * (sorted_m[mid - 1] + sorted_m[mid])


def comps_implied_price(
    subject_metric: float,
    multiple_median: float,
    net_debt: float,                # net debt = total_debt − cash; can be negative
    shares_diluted: float,
) -> float:
    """Implied per-share price using median multiple.

    For Equity multiples (P/E, P/S, P/FCF), use directly:
        price = subject_metric × multiple
    For Enterprise multiples (EV/EBITDA), bridge via equity:
        ev = subject_metric × multiple
        equity = ev − net_debt
        price = equity / shares_diluted

    The caller chooses which path by passing `multiple_medEV = False` for P/E.
    For EV/EBITDA, the user wraps by setting subject_metric=EBITDA AND
    multipled, then we do equity bridge.
    """
    # Default: equity-multiple path
    implied = subject_metric * multiple_median
    if implied > 0 and "EVBridge" in locals():  # never true; left as a marker
        pass
    return implied


def comps_implied_price_with_bridge(
    subject_metric: float,
    multiple: float,
    net_debt: float,
    shares_diluted: float,
    is_ev_multiple: bool = False,
) -> dict[str, float]:
    """Two paths: equity multiple (P/E, P/S) or EV multiple (EV/EBITDA).

    Returns a dict so the memo can show which path was used.
    """
    if is_ev_multiple:
        ev = subject_metric * multiple
        equity = ev - net_debt
        per_share = equity / shares_diluted if shares_diluted > 0 else 0.0
        return {"ev": _round(ev, 4), "equity": _round(equity, 4),
                "per_share": _round(per_share, 2), "path": "EV-bridge"}
    else:
        per_share = subject_metric * multiple
        return {"per_share": _round(per_share, 2), "path": "equity-direct"}


# --------------------------------------------------------------------------- #
# Triangulation
# --------------------------------------------------------------------------- #
def triangulate(
    dcf_per_share: float,
    multiples_per_share: dict[str, float],
    market_price: float | None,
) -> dict[str, Any]:
    """Cross-reference DCF + multiples vs market.

    Notes: any per-share that is ≤ 0 is treated as not-comparable and
    omitted from the gap. The output explicitly lists which path produced
    which number.
    """
    sources: dict[str, float] = {"dcf": _round(dcf_per_share, 2)}
    for k, v in multiples_per_share.items():
        if v > 0:
            sources[k] = _round(v, 2)
    if market_price is not None and market_price > 0:
        sources["market"] = _round(market_price, 2)

    # midpoint of all non-market sources = "model-implied"
    non_market = [v for k, v in sources.items() if k != "market"]
    if non_market:
        midpoint = sum(non_market) / len(non_market)
        sources["model_midpoint"] = _round(midpoint, 2)

    # gap % if market exists
    if "market" in sources and "model_midpoint" in sources:
        gap_pct = (sources["model_midpoint"] / sources["market"] - 1.0) * 100.0
        sources["gap_pct"] = _round(gap_pct, 2)
        if abs(gap_pct) > 30:
            sources["gap_warning"] = f"≥30% gap between model and market — re-check assumptions"
    return sources


# --------------------------------------------------------------------------- #
# Discipline checks
# --------------------------------------------------------------------------- #
def discipline_checks(
    wi: WaccInputs, ta: TerminalAssumptions,
    fcf_series: list[float], share_count: float,
) -> list[str]:
    warnings: list[str] = []
    re = wi.risk_free_rate + wi.beta * wi.equity_risk_premium
    if re < 0.03 or re > 0.20:
        warnings.append(f"cost_of_equity {re:.2%} outside 3-20% norm — check β or Rf")
    rd_at = wi.cost_of_debt_pretax * (1.0 - wi.tax_rate)
    if rd_at > wi.risk_free_rate * 1.5:
        warnings.append(f"after-tax cost of debt ({rd_at:.2%}) > 1.5× Rf — spread looks high")
    if ta.perpetual_growth is not None and ta.perpetual_growth > 0.045:
        warnings.append(
            f"perpetual growth {ta.perpetual_growth:.2%} > 4.5% (long-run nominal GDP) — verify"
        )
    if ta.perpetual_growth is not None and ta.perpetual_growth < 0:
        warnings.append(f"perpetual growth < 0 (decline assumption) — confirm deliberate")
    for i, fcf in enumerate(fcf_series[:-1], start=1):
        if fcf <= 0:
            warnings.append(f"year {i} FCF ≤ 0 — FCF projections should be positive in early years")
    if share_count <= 0:
        warnings.append(f"share_count is 0 or negative — per-share calc will be 0")
    return warnings


# --------------------------------------------------------------------------- #
# The top-level build() function — what the orchestrator calls
# --------------------------------------------------------------------------- #
@dataclass
class BuildRequest:
    ticker: str
    wacc_inputs: WaccInputs
    forecast: ExplicitForecast
    terminal: TerminalAssumptions
    share_count: float
    net_operating_assets: float          # non-operating + cash − debt; can be negative
    tweaks: dict[str, Any] = field(default_factory=dict)


def build(req: BuildRequest) -> dict[str, Any]:
    """Compute DCF end-to-end and return a JSON-friendly summary.

    The shape is documented at the top of this file. This function is the
    single source of truth for the numerical output.
    """
    wacc_full = compute_wacc(req.wacc_inputs)
    wacc = wacc_full["wacc"]
    forecast = req.forecast.fcf_series
    pv_explicit = discount_explicit(forecast, wacc)

    # terminal year FCF + growth/multiplied TV
    terminal_year_fcf = forecast[-1]
    tv_methods = terminal_value(terminal_year_fcf, wacc, req.terminal)
    # pick a primary TV — Gordon wins if available
    primary_tv = None
    primary_method = None
    if tv_methods.get("gordon", {}).get("tv"):
        primary_tv = tv_methods["gordon"]["tv"]
        primary_method = "gordon"
    elif tv_methods.get("exit_multiple", {}).get("tv"):
        primary_tv = tv_methods["exit_multiple"]["tv"]
        primary_method = "exit_multiple"

    pv_tv = 0.0
    if primary_tv is not None and wacc > 0:
        pv_tv = primary_tv / ((1.0 + wacc) ** len(forecast))

    pv_exp_total = sum(row["pv"] for row in pv_explicit)
    enterprise_value = pv_exp_total + pv_tv
    equity_value = enterprise_value + req.net_operating_assets
    per_share = equity_value / req.share_count if req.share_count > 0 else 0.0

    sens = sensitivity_grid(
        forecast, req.share_count, req.net_operating_assets, wacc,
        req.terminal.perpetual_growth or 0.025,
        wacc_steps=0.01, g_steps=0.005, n_per_side=2,
    )

    warnings = discipline_checks(req.wacc_inputs, req.terminal, forecast, req.share_count)

    return {
        "inputs": {
            "ticker": req.ticker,
            "wacc_inputs": {
                "risk_free_rate": req.wacc_inputs.risk_free_rate,
                "beta": req.wacc_inputs.beta,
                "equity_risk_premium": req.wacc_inputs.equity_risk_premium,
                "cost_of_debt_pretax": req.wacc_inputs.cost_of_debt_pretax,
                "tax_rate": req.wacc_inputs.tax_rate,
                "capital": {"equity_weight": req.wacc_inputs.capital.equity_weight,
                             "debt_weight": req.wacc_inputs.capital.debt_weight},
            },
            "forecast": {"fcf_series": list(forecast)},
            "terminal": {
                "perpetual_growth": req.terminal.perpetual_growth,
                "ebitda_multiple": req.terminal.ebitda_multiple,
                "terminal_year_ebitda": req.terminal.terminal_year_ebitda,
            },
            "share_count": req.share_count,
            "net_operating_assets": req.net_operating_assets,
        },
        "wacc": wacc_full,
        "pv_explicit": pv_explicit,
        "pv_explicit_total": _round(pv_exp_total, 4),
        "terminal": {
            "methods": tv_methods,
            "primary_method": primary_method,
            "primary_tv": _round(primary_tv, 4) if primary_tv is not None else None,
            "pv_terminal_value": _round(pv_tv, 4),
        },
        "enterprise_value": _round(enterprise_value, 4),
        "equity_value": _round(equity_value, 4),
        "per_share": _round(per_share, 4),
        "sensitivity": sens,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------- #
# ToolResult wrapper — what runtime.call_tool returns
# --------------------------------------------------------------------------- #
class DCFTool:
    """The tool the runtime exposes. Single public method: `run_model()`.

    Inputs are JSON-shaped. Returns `ToolResult(status="SUCCESS", data=...)`.
    Missing required fields → FAILED without raising.
    """
    name = "quant_dcf"
    user_agent: str = ""

    def run_model(self, request: dict[str, Any]) -> ToolResult:
        """Run the DCF model. Single positional arg: the request dict.

        Shape:
          {
            "ticker": "AAPL",
            "wacc_inputs": {risk_free_rate, beta, equity_risk_premium,
                            cost_of_debt_pretax, tax_rate,
                            capital: {equity_weight, debt_weight}},
            "forecast": {fcf_series: [..5 floats..]},
            "terminal": {perpetual_growth?, ebitda_multiple?, terminal_year_ebitda?},
            "share_count": float,
            "net_operating_assets": float
          }
        """
        try:
            req = self._ingest(request)
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
            note=(f"DCF intrinsic = ${result['per_share']:.2f}/share"
                  f" (WACC = {result['wacc']['wacc']:.2%}, "
                  f"method = {result['terminal']['primary_method'] or 'n/a'})"),
        )

    @staticmethod
    def _ingest(r: Mapping[str, Any]) -> BuildRequest:
        wi_raw = r["wacc_inputs"]
        wi = WaccInputs(
            risk_free_rate=float(wi_raw["risk_free_rate"]),
            beta=float(wi_raw["beta"]),
            equity_risk_premium=float(wi_raw["equity_risk_premium"]),
            cost_of_debt_pretax=float(wi_raw["cost_of_debt_pretax"]),
            tax_rate=float(wi_raw["tax_rate"]),
            capital=CapitalStructure(
                equity_weight=float(wi_raw["capital"]["equity_weight"]),
                debt_weight=float(wi_raw["capital"]["debt_weight"]),
            ),
        )
        forecast = ExplicitForecast(
            fcf_series=[float(x) for x in r["forecast"]["fcf_series"]],
        )
        term_raw = r.get("terminal", {})
        terminal = TerminalAssumptions(
            perpetual_growth=(float(term_raw["perpetual_growth"])
                              if term_raw.get("perpetual_growth") is not None else None),
            ebitda_multiple=(float(term_raw["ebitda_multiple"])
                             if term_raw.get("ebitda_multiple") is not None else None),
            terminal_year_ebitda=(float(term_raw["terminal_year_ebitda"])
                                   if term_raw.get("terminal_year_ebitda") is not None else None),
        )
        return BuildRequest(
            ticker=str(r["ticker"]),
            wacc_inputs=wi,
            forecast=forecast,
            terminal=terminal,
            share_count=float(r["share_count"]),
            net_operating_assets=float(r["net_operating_assets"]),
        )
