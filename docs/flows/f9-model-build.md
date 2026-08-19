# Flow f9 — Model Build (DCF + Comps)

> *"Build me the actual numbers — what's the intrinsic price range, and how does it compare to multiples and the market?"* — the flow that produces a **defensible valuation**, not a vibes-feel memo.

## What it answers

> *Given a senior-analyst thesis on [TICKER], what's the intrinsic value (DCF), what does the peer multiples say, and where's the gap to market?*

The deliverable is a **model envelope**, not a narrative memo. The final-report agent renders it as prose for the user, but the **envelope itself** is the system's output — citation-ready, defensible, auditable.

A Wharton-team-quality memo almost always has a number in the bottom-line — "intrinsic $96.77 / share, multiples-implied $215.06, market $195, model midpoint $155.91, gap -20%." We produce that gap honestly.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|-------------------|
| `ticker` | yes | The ticker for the model (e.g. `AAPL`) |
| `thesis_synthesis` | auto-loaded | Senior-analyst's output: drives bull/bear frame for the FCF projections |
| `flow_context` | optional | User portfolio — informs whether to over-weight one scenario |
| `depth` | optional | `STANDARD` (5Y forecast + 1 sensitivity grid) or `DEEP` (10Y forecast + 2 grids) |
| `compressed` | optional | `bool` — `true` strips detail out of the memo |
| `model` | required | `--model ollama/llama3.3:70b \| anthropic/claude-sonnet-4-5` |
| `paid_for` | optional | Hybrid routing: typically `--paid-for model-builder` |
| `as_of` | optional | Override today; defaults to runtime `now()` |

## Wave plan — **serial, deliberately not parallel**

| Wave | Agent | Role |
|---|---|---|
| 1 | senior-analyst | Frames thesis (bull/bear + key takeaways) — informs FCF projections |
| 2 | model-builder | Parametric envelope (WACC, FCF, comps, scenarios, sensitivity, triangulation) |
| 3 | devils-advocate | Attacks the model's **inputs**: "your β is wrong," "your peer set excludes NVDA unfairly," "your terminal growth is too aggressive" |
| 4 | final-report | Memo framing the model with bull/bear/triangulation |

**Why serial, not parallel:** DCF requires sequential reasoning — thesis → FCF projections → WACC → discount → TV → per-share → comps triangulation. Parallel waves would produce inconsistent per-share values because the comps set depends on what FCF trajectory was assumed.

The LLM in wave 2 doesn't actually compute — it **populates** the math. The math runs in `runtime.tools.dcf` and `runtime.tools.comps` deterministically.

## Math contract (deterministic, not LLM)

Wave 2 calls two tools via `runtime.call_tool`:

### `quant_dcf` (WACC + PV + TV + per-share)
```
Inputs: {ticker, wacc_inputs, forecast.fcf_series[5], terminal.perpetual_growth|ebitda_multiple,
         share_count, net_operating_assets}
Outputs: WACC, PV(5Y FCFs), TV, PV(TV), EV, equity, per-share_base,
         sensitivity_grid (WACC × g), warnings[]
```

### `quant_comps` (peer median + implied price)
```
Inputs: {subject: {ticker, metrics{ev_ebitda, p_e_ntm, ...}, net_debt, shares_diluted},
         peers: [{ticker, metric, multiple, as_of}, ...]}
Outputs: per metric: {peer_median, peer_trimmed_mean, peer_min, peer_max,
                       implied: {per_share, ev, equity, path="EV-bridge|equity-direct"}},
         warnings[]
```

## Discipline ✓

| Check | What it guards against | Where |
|---|---|---|
| WACC in [3%, 20%] | Mis-typed β, weird weights | tool warning + memo flag |
| Perpetual growth ≤ 4.5% (US) | Hand-wavy terminal assumption | tool warning |
| Two scenarios (base + bear) required | Single-frame puff pieces | envelope check |
| Sensitivity ±100bps × ±50bps | "The intrinsic is $X, full stop" claims | envelope check |
| Comps size-matched + sector-matched | Mixed-sector checklists | optional note, not enforced |
| Every input cited (source) | Hallucinated WACC, fabricated peer multiples | citations[] in envelope |
| Citations verifiable against `_runs/<id>/` | Made-up URLs | `test_source_verification.py` |

## What this flow does **NOT** do

- Does not produce a "true" price. The output is a **range** from the sensitivity grid, triangulated against comps.
- Does not generate trading recommendations. The bottom-line direction comes from `senior-analyst`, not this flow.
- Does not assume LLM math. WACC, PV, TV, per-share, sensitivity — all pure Python. The LLM only fills inputs.
- Does not skip citations. Each WACC input, each FCF driver, each comp requires a source.

## Sample envelope shape (AAPL FY2024 backtest)

```
{
  "agent_id": "model-builder",
  "ticker": "AAPL",
  "model": {
    "wacc_inputs": {Rf: 4.30%, β: 1.24, ERP: 5.50%, Kd: 3.50%, T: 16%, E/D: 96/4},
    "forecast": {fcf_series_5y: [115.5, 121.3, 127.4, 132.5, 137.8] B USD},
    "terminal": {perpetual_growth: 3.00%},
    "comps": {
      peer_set: [MSFT 28x, GOOGL 22x, META 22x, AMZN 24x, NVDA 45x, NFLX 40x],
      peer_median_ev_ebitda: 26x,
    },
    scenarios: [
      {name: "base", intrinsic_per_share: 96.77},
      {name: "bear", intrinsic_per_share: 71.20},
    ],
    sensitivity_dimensions: [wacc, terminal_g]
  },
  result_summary: {
    dcf_intrinsic_per_share_base: 96.77,
    dcf_intrinsic_per_share_bear: 71.20,
    comps_implied_per_share_ev_ebitda: 215.06,
    comps_implied_per_share_p_e_ntm: 262.50,
    model_midpoint_per_share: 155.91,
    triangulation_vs_market: {gap_pct: -20%, gap_warning: "DCF vs comps wide; verify assumptions"}
  },
  confidence: "MEDIUM"
}
```

## Maturity checklist (what f9 needs to be production-ready)

- [x] `runtime/tools/dcf.py` — math runs correctly (hand-test against AAPL matches)
- [x] `runtime/tools/comps.py` — peer median + EV-bridge + equity-direct
- [x] `runtime/call_tool.py` — `quant_dcf` + `quant_comps` registered
- [x] `docs/prompts/leads/model-builder/system-prompt.md` — discipline applied in agent prompt
- [x] `runtime.execute_flow_f9` — orchestrator wires 4 agents serially
- [x] `runtime.run_flow_stream` — supports flow_id="f9"
- [x] `runtime.main` — `--flow f9` arg added
- [x] `validate_envelope` — model-builder fields required
- [ ] Real-LLM smoke against Ollama (next obvious step)
- [ ] Pressure-test pilot: plug in a forward consensus + actual print, assert defensible range

See `docs/TODO.md` [smoke-1] for the real-LLM step.
