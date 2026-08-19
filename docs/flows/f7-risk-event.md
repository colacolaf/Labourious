# Flow f7 — Risk Event

> *"[News event] just hit — what's the read?"* — same-day event-driven analyst task.

## What it answers

> *"Given [specific news event] affecting names [X, Y, Z], which are most exposed, what's the magnitude, what's the duration, what should I do at the open?"*

Speed matters more than depth here. **Same-day-or-faster wallclock** is the contract. The trade-off: tighter memo, more certitude in citing primary sources from the news cycle.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `event` | yes | Free-form: `"NVDA reports China export ban"`, `"Fed signals 50bp cut"` |
| `exposed_tickers` | required | Universe the user wants assessed for exposure. |
| `event_horizon` | optional | `intraday | 1-3 days | 1-4 weeks`. Default `1-4 weeks`. |
| `depth` | optional | Default SCAN. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Wave 1 (sequential):
  ➤ senior-analyst (DEPTH=SCAN — event frame)
       - frame the event (systemic vs idiosyncratic, reversible vs durable, market-moving magnitude)
       - identify exposure rubric

Wave 2 (parallel):
  ➤ forensic-accounting (DEPTH=SCAN)
       - for each exposed ticker: "does the event change the financials?" (1-line per ticker)
  ➤ devils-advocate (DEPTH=SCAN)
       - counter-case: "the market is over-reacting / under-reacting; here's why"

Wave 3 (sequential):
  ➤ final-report with rubric "event impact"
       → exposure map + duration read + action options
```

## Rubric

> **The event-impact memo.**
> Goal: short, sharp, time-sensitive. Same memo template as f3 but for an event, not an earnings print.
>
> Structure:
> 1. **What happened** — 1 paragraph: what the event is, in plain English.
> 2. **Magnitude & duration** — explicit call: `signal duration` = `intraday | 1-3 days | 1-4 weeks | durable (>1 month)` with reasoning.
> 3. **Exposure map** — table: `ticker | exposure (HIGH/MED/LOW) | duration | known-vs-uncertain | 1-line action`.
> 4. **What the market likely mispricing** — 1 paragraph: the framing the market has that may be wrong.
> 5. **Action options** — 3 lines: "do nothing / hedge / trim / add".
> 6. **Citations**.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f7",
  "memo": {
    "what_happened": "...",
    "magnitude_and_duration": { "duration": "durable", "reasoning": "..." },
    "exposure_map": [...],
    "what_market_mispricing": "...",
    "action_options": ["A", "B", "C"],
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Speed test** (added to evals): f7 runs in <10 minutes wallclock on a hybrid config.
- **The Exposure test**: every ticker in `exposed_tickers` appears in `exposure_map` with an exposure label.
- **The Duration test**: `magnitude_and_duration.duration` is one of the four named values, with a 1-line reasoning.

## Skipped calls

- `devils-advocate` at SCAN only — this isn't the place for a full counter-case.
- Forensic-accounting at SCAN unless the user explicitly asked "what does this do to the financials?"

## Wallclock target

- All-free: **3–7 minutes**.
- Hybrid: **2–4 minutes**.

## Cost target

Roughly **0.6× f1**.

## Out of scope (f7)

- Earnings-day pre-mortem. Use f3.
- Multi-day research archive. Use f4 or f1.
- Sector-wide post-event study. Use f5.

## Implementation notes

Implemented in `docs/runtime/runtime.py` as `execute_flow_fN` and wired through
`run_flow_stream` + `--flow fN …` CLI. Behavior:

- **f5 (sector landscape)** — `execute_flow_f5(sector, universe, …)`. Per-ticker
  parallel fan-out (ThreadPoolExecutor) of senior + devil, then comparator via
  `runtime.call_tool("quant_comparator", …)`, then final-report. Min 5 tickers.
  Same rubric semantics as f2.
- **f6 (thematic screen)** — `execute_flow_f6(thesis, seed_universe, …)`. Two-pass:
  cheap SCAN on the universe, prune to `shortlist_size`, then STANDARD on
  survivors. Comparator + final-report on survivors.
- **f7 (risk event)** — `execute_flow_f7(event, exposed_tickers, …)`. Speed-priority:
  SCAN depth through all agents. Single senior framing, parallel per-ticker
  forensic + devil, then final-report. No thesis-register write.
- **f8 (macro overlay)** — `execute_flow_f8(macro_shock, thesis_ids, …)`.
  Pre-wave loads prior theses; parallel per-thesis senior + devil under macro;
  final-report returns per-thesis vulnerability + portfolio memo.

Pilot: `f5_f8_pilot.py` — 22/22 green.

Dry-run smoke:

```bash
python docs/runtime/runtime.py --flow f5 --tickers AAPL,MSFT,GOOGL,META,AMZN,NVDA \
    --thesis "Big Tech" --dry-run
python docs/runtime/runtime.py --flow f6 --tickers AAPL,MSFT,GOOGL,META,AMZN,NVDA \
    --thesis "AI beneficiaries" --dry-run
python docs/runtime/runtime.py --flow f7 --ticker NVDA \
    --thesis "export-control update" --dry-run
python docs/runtime/runtime.py --flow f8 \
    --thesis "Fed cuts 50bps on 2026-09-15" --dry-run
```
