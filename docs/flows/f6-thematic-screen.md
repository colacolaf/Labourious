# Flow f6 — Thematic Screen

> *"Find names that match [a thesis]."* — the analyst's first-pass screen.

## What it answers

> *"Given [thesis verbatim from the user], produce a ranked list of 5–15 tickers that best fit the thesis, with each one's fit-rationale in 2–3 lines."*

This is **the cost-compressed flow**. It runs the orchestrator in batch over a candidate set with DEPTH=SCAN, then re-runs only the survivors at STANDARD. **Most of the cost is in the deep passes on shortlist; the screening pass is cheap.**

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `thesis` | yes | The thematic claim (e.g. `"AI infrastructure plays with sub-30% sales multiples"`). |
| `seed_universe` | optional | Starting set; default is the user's flow_context portfolio + a known universe. |
| `max_universe` | optional | Hard cap on tickers screened; default 30. |
| `shortlist_size` | optional | Target survivors; default 10. |
| `depth` | optional | Default SCAN for the screen pass; STANDARD for survivors. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Pre-wave (loops over candidate universe):
  ➤ for each candidate in `seed_universe` (capped at `max_universe`):
       senior-analyst (DEPTH=SCAN — does it match the thesis? 2-line verdict)
       → verdict: STRONG_FIT | WEAK_FIT | NO_FIT

  → top `shortlist_size` by STRONG_FIT count + cross-name composability

Wave 2 (parallel over shortlist):
  ➤ for each shortlisted ticker:
       forensic-accounting (DEPTH=SCAN) — just the headline financials
       devils-advocate (DEPTH=SCAN) — one bear flag
       → per-ticker fit revised with a concrete note

Wave 3 (sequential):
  ➤ final-report with rubric "thematic screen"
       → ranked list with fit-rationale
```

**Devils-advocate on f6 fights group-think**: if 5 of 6 candidates are saying the same thing, the bear case surfaces the obvious risk everyone is missing.

## Rubric

> **The screen memo.**
> Goal: produce a ranked shortlist the user can dive into with f1 per name, plus the rationale so the user understands *why* the shortlist looks the way it does.
>
> Structure:
> 1. **Bottom line** — thesis fit ± 1 conviction; one-line summary of the shortlist.
> 2. **Shortlist** — ranked table: `rank`, `ticker`, `fit_score`, `fit_rationale`, `1-line bear flag`.
> 3. **What's missing from the shortlist** — 1 paragraph: *the obvious candidate that didn't make it, and why.*
> 4. **Group-think check** — 1 paragraph: *the bear view the shortlist collectively misses.*
> 5. **Recommended next step** — "Run f1 on rank-1, then compare top-3 via f2".
> 6. **Citations**.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f6",
  "memo": {
    "bottom_line": {...},
    "shortlist": [
      { "rank": 1, "ticker": "...", "fit_score": "...", "fit_rationale": "...", "bear_flag": "..." }
    ],
    "missing_from_shortlist": "...",
    "group_think_check": "...",
    "recommended_next": "...",
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Shortlist test** (added to evals): exactly `shortlist_size` items in the table; no more, no fewer (unless universe is too small).
- **The Group-think test**: the `group_think_check` paragraph is present and identifies at least one specific risk the shortlist collectively misses.
- **The Diversity test**: shortlist is not just one sector (unless the thesis demands it).

## Skipped calls

- None at SCAN (the screen is itself a SCAN).
- Top-of-shortlist candidates may run DEEP senior-analyst — optional, only when the user requests it.

## Wallclock target

- 30 names SCAN pass + 10 survivors STANDARD: **20–30 minutes** all-free.
- 15 names + 5 survivors: **12–18 minutes** all-free.

## Cost target

| Universe | Cost target |
|----------|------------|
| 15 names + 5 survivors | $0.10–$0.30 |
| 30 names + 10 survivors | $0.20–$0.60 |

## Out of scope (f6)

- Sector-by-sector ranking. Use f5.
- Single-name deep-dive. Use f1 on the shortlist survivor.
- Strategy / allocation talk. The screen is about *what to look at*, not *what to do*.

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
