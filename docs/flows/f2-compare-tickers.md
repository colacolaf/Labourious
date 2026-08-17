# Flow f2 — Compare Tickers

> *"A vs B vs C — which one wins?"* — today's most common second-pass analyst task after coverage initiation.

## What it answers

> *"Among [2–5 tickers], which one best fits my thesis at the current price? Conviction-ranked, side-by-side."*

The deliverable is a single ranked pick with confidence, **with a per-ticker mini-memo attached**. The user pastes the table into a meeting; the individual memos back it up.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `tickers` | yes | 2–5 tickers (e.g. `["NVDA", "AMD", "TSM"]`). |
| `rubric` | optional | Comparison rubric (e.g. "fastest AI accelerator growth"). |
| `flow_context` | optional | User's book, constraints. |
| `depth` | optional | Default STANDARD. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Pre-wave (sequential, loops over tickers):
  ➤ for each ticker:
       senior-analyst (DEPTH=SCAN) — single-sentence thesis
       → collects into a candidate matrix on a normalized rubric

Wave 2 (sequential, top-N chosen):
  ➤ for each shortlisted ticker:
       forensic-accounting (DEPTH=STANDARD) + devils-advocate (DEPTH=SCAN — lighter)
       → returns per-ticker findings attached to the matrix

Wave 3 (sequential):
  ➤ final-report (rubric: "side-by-side, ranked")
       → produces comparison table + ranking + ranked pick
```

**F2's pattern: many SCAN passes, then fewer STANDARD passes, then a final-report with the comparison rubric.** This compresses the ~15× cost of f1's full chain by only running deep analysis on shortlist survivors.

## Rubric

> **Side-by-side comparison, ranked.**
> Goal: produce a table where every ticker is scored on the same normalizable dimensions, plus a ranked pick with conviction.
>
> The deliverable structure:
> 1. **One-line summary** — direction + conviction for the ranked pick.
> 2. **Comparison table** — 6–10 normalized dimensions (P/E vs cohort, growth, margin trend, balance-sheet strength, momentum, sentiment, etc.). The dimensions must be **the same across all rows**. This is the comparison contract.
> 3. **Per-ticker mini-memo** — 5–7 lines each, with one citation.
> 4. **Ranking** — 1–N, with the ranking rationale in 1 paragraph.
> 5. **What an attacker would say about the top pick** — 1 paragraph.
> 6. **Citations** — list.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f2",
  "memo": {
    "summary": "...",
    "comparison_table": [
      { "ticker": "AAPL", "dimension1": "..." , "dimension2": "..." , ... }
    ],
    "per_ticker_mini_memos": [
      { "ticker": "AAPL", "memo": "5-7 lines with 1 citation" }
    ],
    "ranking": [{ "rank": 1, "ticker": "AAPL", "rationale": "..." }],
    "top_pick_attack": "1 paragraph",
    "citations": [...]
  },
  "confidence": "...",
  "verification": {...}
}
```

## Acceptance

- All 5 standard evals pass.
- **The Comparison test** (added to evals): every ticker in `tickers` appears in every row of the comparison_table; no missing or NaN cells.
- **The Normalization test**: the same dimensions appear across all rows in the same order. Apples-to-apples, not apples-to-oranges.
- **The Ranking test**: a single top-pick is named, with conviction, and a ranked list of the rest.
- A skeptical human sees the comparison table in 30 seconds and could give a confident answer to "which one?".

## Skipped calls

- Standard `devils-advocate` at SCAN (cheaper than f1) — but DEEP if any of the survivors is highly ranked.
- `forensic-accounting` only runs on the shortlist (top-N), not on all input tickers — this is the cost optimisation.

## Out of scope (f2)

- Single-ticker thesis. Use f1.
- Sector-wide landscape >10 names. Use f5 or f6.
- Portfolio-level allocation. Use a future portfolio-aware flow.

## Wallclock target

- 5 tickers + top-3 shortlisted: **10–15 minutes** all-free.
- 2 tickers, full depth: **8–12 minutes** all-free.

## Cost target

- Tiered cheaper than f1: shortlist-first pays off.
- All-free 5-ticker f2: **~$0**.
- Hybrid f2 (3 shortlisted, full depth + Sonnet synthesis): **~$0.20**.
