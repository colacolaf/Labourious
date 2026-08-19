# Flow f8 — Macro Overlay

> *"How does [macro shock] hit my thesis?"* — for users with an existing position (in the thesis_register) and a question about the macro backdrop.

## What it answers

> *"Given [macro event — Fed cut, rate move, currency shock, geopolitical event, supply-chain shock, etc.], how should I update the theses I already hold?"*

This is the **thesis-aware macro frame**. Unlike f7 (which is event-driven on a specific news), f8 is **portfolio-aware on a macro**: you've got theses in your `thesis_register`; a macro variable changes; run f8 to see how the theses shift.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `macro_shock` | yes | `"Fed cuts 50bp"`, `"USD weakens to 110 vs EUR"`, `"China-Taiwan escalation"`, etc. |
| `thesis_ids` | required | List of thesis_register rows the user wants re-run against this macro. |
| `horizon` | optional | `1m | 3m | 6m | 12m`. Default 6m. |
| `depth` | optional | Default STANDARD. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Wave 1 (sequential):
  ➤ senior-analyst (DEPTH=STANDARD — macro framing)
       - frame the shock (transmission channels — rates / FX / cycle / supply chain)
       - for each thesis in `thesis_ids`: re-read its `bottom_line`, `fragile_assumption`, `next_three_questions` from thesis_register
       - construct the per-thesis vulnerability rubric

Wave 2 (parallel over thesis_ids):
  ➤ forensic-accounting (DEPTH=SCAN per thesis)
       - "does the macro change the financials materially?" (1-line)
  ➤ devils-advocate (DEPTH=STANDARD per thesis)
       - "does the thesis break under this macro?" (full counter-case)

Wave 3 (sequential):
  ➤ final-report with rubric "macro overlay"
       → per-thesis position + portfolio-level summary
```

## Rubric

> **The macro-overlay memo.**
> Goal: produce a per-thesis vulnerability read with a portfolio-level summary, plus a recommended action.
>
> Structure:
> 1. **Bottom line** — net portfolio-level direction (more bullish / more bearish + conviction + flip trigger).
> 2. **Macro transmission map** — 1 paragraph: how the shock flows to the theses (rate channel, FX channel, demand channel, etc.).
> 3. **Per-thesis overlay** — table: `ticker | current thesis direction | macro read (BENIGN/NEUTRAL/NEGATIVE/SEVERE) | new thesis direction | new bottom-line conviction | new flip trigger`.
> 4. **Top-1 thesis to act on** — 1 paragraph: the one position that needs immediate action (if any).
> 5. **What an attacker would say** — 1 paragraph: the bear view the portfolio thesis collectively misses.
> 6. **Citations**.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f8",
  "memo": {
    "bottom_line": {...},
    "macro_transmission": "...",
    "per_thesis_overlay": [
      { "ticker": "...", "current_direction": "HOLD", "macro_read": "NEGATIVE", "new_direction": "SELL", "new_conviction": 3, "new_flip_trigger": "..." }
    ],
    "top_1_to_act": "...",
    "portfolio_attack_view": "...",
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Coverage test** (added to evals): every `thesis_id` appears in `per_thesis_overlay` with all 6 fields populated.
- **The Macro-link test**: `macro_transmission` is not generic ("rates affect everything") — it names at least 2 specific channels (e.g. *"the channel is the rate sensitivity of consumer-discretionary earnings; the secondary channel is investor positioning in long-duration assets"*).
- **The Action test**: a clear top-1-to-act is named when the macro is material; if no action, the memo says so explicitly.

## Skipped calls

- None normally. `devils-advocate` is essential here — the macro break-test is the heart of the flow.
- Forensic-accounting may be SCAN if the user wants the macro read but not the financial refresh.

## Wallclock target

- 5 theses overlay: **8–12 minutes** all-free.
- 10 theses: **15–25 minutes** all-free.

## Cost target

Roughly **0.8× f1 per thesis**.

## Out of scope (f8)

- Single-thesis macro re-examination. The user has multiple theses; for a single-name macro read, use f4 if "earnings print" timeframe or f1 if the agent needs a full re-thesis.
- New thesis initiation. Use f1.
- Sector-wide macro read. Use f5 with rubric-name = macro tag.

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
