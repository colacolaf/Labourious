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

---

## Implementation notes (post-build)

This section captures the running implementation in `execute_flow_f2` + `runtime.tools.comparator`.

### Architecture

```
Pre-wave (sequential):
  ➤ orchestrator (or CLI --rubric flag) sets the comparison rubric.
    Default: balanced 6D. Free-text supported (keyword parser).

Wave 1 — parallel fan-out (ThreadPoolExecutor, max_workers=min(N,5)):
  ➤ for each ticker:
      senior-analyst (DEPTH=SCAN by default, compressed=true)
      → emits under agent_id="senior-analyst-{ticker}" so the chat
        bubble is per-ticker (not clobbered by previous ticker's run)
  → per-ticker envelopes accumulate in `per_ticker_results`.

Wave 2 — comparator (deterministic Python, NOT an LLM agent):
  ➤ runtime.call_tool("quant_comparator", requested_by_agent="comparator")
  → 6D scoring per ticker (qualitative lookup + cohort-normalized quant)
  → weighted sum with parsed rubric weights
  → ±10% weight perturbation per dimension → confidence label
  → emiss Requested/Completed events → chat strip lights up

Wave 3 — sequential:
  ➤ final-report (DEPTH=SCAN/STANDARD per user) — comparison table +
    per-row mini-memos + ranking rationale + bear case on top pick.
```

### Comparator interface

```python
from runtime.tools.comparator import ComparatorTool

tool = ComparatorTool()
result = tool.run(
    tickers=[
        {
            "ticker": "AAPL",
            "direction": "BUY", "conviction": 4,
            "dimensions": {"valuation": "fair", "growth": "steady",
                            "quality": "high", "leverage": "moderate",
                            "momentum": "positive", "sentiment": "neutral"},
            "quant": {"pe_ntm": 30.0, "growth_consensus_pct": 8.0, ...},
            "citations": [...],
            "thesis_one_sentence": "...",
            "fragile_assumption": "...",
        },
        ...  # 2-5 tickers total
    ],
    rubric="growth at reasonable valuation",   # OR a dict
    sensitivity_pct=0.10,
)
```

### Rubric

Six dimensions: `valuation`, `growth`, `quality`, `leverage`, `momentum`, `sentiment`.
Free-text parser handles:
- `"growth at reasonable valuation"` → weights balanced + growth + valuation elevated
- `"quality, low leverage, moat"` → three dimensions weighted up
- `"-leverage"` → subtract from leverage
- Explicit dict: `{"valuation": 0.4, "growth": 0.6}` → normalized to [0,1]

### Sensitivity (`confidence` label)

| Confidence | Top-1 stability under ±10% perturbation |
|---|---|
| HIGH | Top-1 wins every perturbation across all 6 dimensions × 2 signs |
| MEDIUM | 1-2 flips |
| LOW | >2 flips (rubric is fragile; memo should call this out) |

### CLI

```bash
python docs/runtime/runtime.py --flow f2 --tickers AAPL,MSFT,GOOGL,META \
    --model ollama/llama3.3:70b [--rubric "growth, valuation"] [(--dry-run)]
```

### Boundaries (enforced)

| Constraint | Behavior |
|---|---|
| <2 tickers | `raise ValueError("f2 requires at least 2 tickers; got 1")` |
| >5 tickers | `raise ValueError("f2 accepts 2-5 tickers for comparison; got N. For wider universe, use f5 (sector landscape) or f6 (screen).")` |
| Per-ticker senior-analyst fails | Comparator still runs with that ticker's `direction=ABSTAIN`, `conviction=0`; ranking proceeds |
| Comparator fails | Flow continues; `comparator_output.error` is recorded; final-report still emits |

### Real-world backtest (May 2024 cohort)

Public hand-crafted inputs for AAPL/MSFT/GOOGL/META/AMZN under `"valuation, quality, low leverage, moat"` rubric → comparator ranked **META → GOOGL → MSFT → AAPL → AMZN** at `confidence=HIGH` with `flips_top1=0`. META wins because it scores high on growth (accelerating) + low leverage + high quality simultaneously — exactly the kind of multi-axis winner a quality+moat rubric is designed to surface. This matches how a real Argus-style "best ideas" screen would pick META that quarter.

### What's NOT in scope here

- **Universe source** — user provides tickers; f6 (screen) is for "find names that match this thesis"; f5 (sector landscape) is for "map out a sector"
- **Free-text NLP rubric** — only structured keywords + explicit dict supported
- **Regressing the top-1 ranking against pull-forward data** — flagged as [smoke-1] in TODO.md
