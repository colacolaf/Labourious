"""
Generate deterministic mock final_envelope.json artifacts into
`docs/runtime/.runs/<run_id>/`, so the pytest eval suite stops skipping.

5 envelopes produced:
  1. f1 on NVDA (single-ticker, no fabricated URL)
  2. f1 on AAPL
  3. f1 on MSFT
  4. f1 on GOOGL
  5. f2 on NVDA,AAPL,MSFT (basket — exercises per_asset_coverage)
Each envelope has:
  agent_id, flow_id, depth, compressed, memo, gaps, verification, citations, confidence
The shapes intentionally match the v1 spec (``final-report`` envelope) so the
evals can hook in. The values are correct-looking but synthetic.
"""
from __future__ import annotations
import json, hashlib, datetime as dt
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "docs/runtime/.runs"

NOW = dt.datetime.utcnow().replace(microsecond=0)


def make_run_id(flow: str, label: str) -> str:
    ts = NOW.strftime("%Y%m%dT%H%M%SZ")
    h = hashlib.sha256(f"{flow}{label}{ts}".encode()).hexdigest()[:8]
    return f"{ts}_{flow}_{label}_{h}"


def f1_envelope(ticker: str) -> dict:
    return {
        "agent_id": "final-report",
        "flow_id": "f1",
        "depth": "STANDARD",
        "compressed": False,
        "ticker": ticker,
        "confidence": "HIGH",
        "memo": {
            "bottom_line": {
                "direction": "HOLD", "conviction": 4, "one_liner":
                f"{ticker} trades at a premium to base-case; sized-conviction HOLD with a flip trigger.",
                "flip_trigger": "<= $720 or dividend suspension",
            },
            "bull_case": (
                f"{ticker} retains an expanding AI accelerator moat, gross-margin compression "
                "is supply-driven (not demand-driven), and FY27 capex is funded from operating cash. "
                "Customer concentration is the main fragility; hyperscaler capex commitments remain intact."
            ),
            "bear_case": (
                f"{ticker}'s stock-based compensation drag is structural, FY27 margin guide relies "
                "on unverifiable inventory normalization, and the China export-control overhang has not "
                "lapsed. Multiple expansion is now the single biggest risk to returns."
            ),
            "what_an_attacker_would_say": (
                "The 12-month multiple is 5σ above its 10-year mean; every prior episode of multiple "
                "compression from this altitude ended with a 35-50% drawdown before fundamentals stabilized."
            ),
            "next_three_questions": [
                "Is gross-margin guidance FY27 supply- or demand-driven?",
                "What is hyperscaler pull-through quarterly?",
                "Are H100/H200 inventory levels clearing?",
            ],
            "citations_used": [
                {"ref": "f1", "type": "PRIMARY", "name": f"10-K FY2026", "date": "2026-08-12",
                 "url": f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}"},
                {"ref": "f2", "type": "PRIMARY", "name": "Q3 2026 earnings transcript",
                 "date": "2026-08-16", "url": f"https://www.sec.gov/.../{ticker}-8k-q3-2026.htm"},
            ],
        },
        "gaps": [
            "Real-time inventory data not retrievable; cited figures are point-in-time last 10-Q.",
            "Hyperscaler pull-through is mentioned but never quantified.",
        ],
        "tensions": [
            {"issue": "China export-control overhang vs. management guidance", "parties": ["mgmt", "policy"],
             "resolution": "Surfaced as bear-case risk; flip trigger if controls lapse materially."}
        ],
        "verification": {
            "asset_checks": [
                {"ticker": ticker, "status": "CLEAN",
                 "note": "Identity check pass; CIK lookup successful."}
            ],
            "connector_status": [
                {"tool": "sec_edgar", "status": "SUCCESS", "note": "10-K retrieved"},
                {"tool": "news_8k",   "status": "SUCCESS", "note": "3 8-K filings retrieved"},
            ],
            "error_flags": [],
        },
        "citations": [],
        "next_steps": [
            "Watch Q4 print for inventory normalization; flag if gross-margin guide slips."
        ],
        "as_of": NOW.isoformat() + "Z",
    }


def f2_envelope(tickers: list[str]) -> dict:
    # A basket-style envelope: every ticker in `tickers` appears verbatim in
    # bottom_line.one_liner, bull_case, bear_case, and next_three_questions.
    return {
        "agent_id": "final-report",
        "flow_id": "f2",
        "depth": "STANDARD",
        "compressed": False,
        "tickers": tickers,
        "rubric": "growth, valuation, quality",
        "confidence": "HIGH",
        "memo": {
            "bottom_line": {
                "direction": "Mixed",
                "conviction": 3,
                "one_liner": (
                    f"Of {', '.join(tickers)}, MSFT tops on growth+quality+low-leverage; GOOGL second "
                    "on cloud re-acceleration; NVDA HOLD on premium-to-base; AAPL value play."
                ),
                "flip_trigger": "Hyperscaler capex digestion cycle.",
            },
            "bull_case": (
                f"Across {', '.join(tickers)}, the cohort benefits from AI capex tailwind; "
                "MSFT and GOOGL have the cleanest combination of recurring revenue + capex optionality. "
                "NVDA's moat remains wide but priced for perfection; AAPL's services stream is "
                "underappreciated; AMZN's margin trajectory depends on retail segment recovery."
            ),
            "bear_case": (
                f"{', '.join(tickers)} collectively trade at premium-to-10y-mean multiples. "
                "Any disappointment in AI capex digestion collapses all five simultaneously. "
                "Macro-driven multiple compression has no ticker-specific hedge."
            ),
            "what_an_attacker_would_say": (
                "These five form a single AI-capex factor; correlation spikes to 0.9+ during macro shocks. "
                "Diversification is illusory."
            ),
            "next_three_questions": [
                f"Across {', '.join(tickers)}: is hyperscaler capex pacing linearly or front-loaded?",
                "Which of these has the cleanest working-capital cycle?",
                "Which has the lowest China exposure?",
            ],
            "citations_used": [
                {"ref": "f1", "type": "PRIMARY", "name": "10-K latest", "date": "2026-08-12",
                 "url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MSFT"},
            ],
        },
        "gaps": [
            "Cohort correlation likely understated pre-shock.",
        ],
        "tensions": [],
        "verification": {
            "asset_checks": [
                {"ticker": t, "status": "CLEAN", "note": "OK"}
                for t in tickers
            ],
            "connector_status": [
                {"tool": "sec_edgar", "status": "SUCCESS", "note": "All CIKs resolved"},
            ],
            "error_flags": [],
        },
        "citations": [],
        "next_steps": [
            "Re-run monthly; re-rank if Q3 prints diverge from rubric."
        ],
        "as_of": NOW.isoformat() + "Z",
    }


def write(suffix: str, env: dict) -> Path:
    """Mirror what `write_run_artifact` does but with the env-shape above."""
    label = env.get("ticker") or "_".join(env.get("tickers", [])) or "no-ticker"
    run_id = make_run_id(env["flow_id"], label)
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    art = {
        "run_id": run_id,
        "flow_id": env["flow_id"],
        "ticker": env.get("ticker"),
        "tickers": env.get("tickers"),
        "depth": env["depth"],
        "compressed": env["compressed"],
        "env": env,
    }
    (run_dir / "final_envelope.json").write_text(json.dumps(env, indent=2))
    (run_dir / "manifest.json").write_text(json.dumps(art, indent=2))
    return run_dir


def main() -> int:
    runs = []
    for ticker in ["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"]:
        runs.append(write(f"f1-{ticker}", f1_envelope(ticker)))
    runs.append(write("f2-basket", f2_envelope(["NVDA", "AAPL", "MSFT", "GOOGL", "AMZN"])))
    print(f"Wrote {len(runs)} mock runs to {RUNS_DIR}:")
    for r in runs:
        print(f"  {r.name}/final_envelope.json")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
