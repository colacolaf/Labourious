# Flow f5 — Sector Deep-Dive

> *"Map out [sector] — who's exposed, who wins, who loses?"* — for sector-allocating analysts (asset managers running sector funds, sector PMs).

## What it answers

> *"Across [sector], which names are positioned to do well, which names are positioned badly, and what's the read on capital flows going into the sector?"*

This is f2 scaled up: instead of 2–5 tickers, it's **a sector's 5–15 most relevant names** plus a cross-name rubric.

## Inputs

| Field | Required? | What it carries |
|-------|-----------|------------------|
| `sector` | yes | e.g. `"AI Infrastructure"`, `"Healthcare"`, `"Banks"` (free-text — flows doesn't restrict; the senior-analyst interprets). |
| `universe` | required | The tickers to cover. 5–15 names typical. |
| `rubric` | optional | Cross-name lens (e.g. "rate-cut exposure"). |
| `depth` | optional | Default STANDARD per ticker; DEEP for top-N survivors. |
| `model` | required | Per-adapter flag. |

## Wave plan

```
Pre-wave (loops):
  ➤ for each ticker in `universe`:
       senior-analyst (DEPTH=SCAN) — "1-line thesis + sector-position claim"
       devils-advocate (DEPTH=SCAN) — "1-line bear + sector-position claim"

  → matrix built on the rubric; shortlist top N by sector position + thesis conviction

Wave 2 (parallel over surviving N):
  ➤ forensic-accounting (DEPTH=STANDARD per shortlisted ticker)
  ➤ devils-advocate (DEPTH=STANDARD — full counter case per shortlisted)

Wave 3 (sequential):
  ➤ final-report with rubric "sector landscape"
       → cross-name memo, capital-flow commentary, ranked picks
```

## Rubric

> **The sector landscape memo.**
> Goal: produce a memo that situates a list of names within a sector, ranks them, and surfaces the capital-flow read.
>
> Structure:
> 1. **Bottom line** — sector view + conviction + flip trigger (e.g. "rate cut, regulatory shift, etc.").
> 2. **Sector overview** — 2–4 paragraphs: what's driving the sector, what's the cross-cutting theme, what capital is doing.
> 3. **Cross-name matrix** — `name`, `thesis one-liner`, `sector-position (positive/neutral/negative)`, `conviction`, `flip trigger`.
> 4. **Top picks** — shortlist, each with a 5-line mini-memo.
> 5. **Avoid / exit list** — names the system thinks are positioned badly; 1 paragraph each on why.
> 6. **What an attacker would say about the sector view** — 1 paragraph.
> 7. **Next three questions** — sector-level (regulatory, macro, customer-concentration).
> 8. **Citations**.

## Sectors are knowledge packs, not agents

**The senior-analyst prompt adopts a sector lens via a short sector-pack appended to its prompt at runtime** — not via a separate agent. Loading a sector pack is:

```python
# in runtime/flow_runner.py
sector_pack = load_sector_pack(sector)  # e.g. "ai-infrastructure.md"
senior_analyst_prompt = senior_analyst_prompt_template.format(
    base=sr_analyst.system_prompt(),
    sector_pack=sector_pack
)
```

This pattern is the **pluggable policy** — *[sectors are knowledge packs, not agents](../DEFERRED.md#1-specificity-lives-in-knowledge-packs-not-agents)*. The senior-analyst prompt accepts a sector pack as a context modifier; no new agent is created for each sector.

We maintain a small **sector-pack library** in `docs/prompts/pluggable/<sector>-pack.md` (per the pluggable policy — knowledge packs are the only thing that ships under `pluggable/`). v1 ships 0–3 packs; more on demand.

## Output

```jsonc
{
  "agent_id": "final-report",
  "flow_id": "f5",
  "memo": {
    "bottom_line": {...},
    "sector_overview": "...",
    "cross_name_matrix": [...],
    "top_picks": [...],
    "avoid_list": [...],
    "sector_attack_view": "...",
    "next_three_questions": [...],
    "citations": [...]
  }
}
```

## Acceptance

- All 5 standard evals pass.
- **The Coverage test** (added to evals): every ticker in `universe` appears in `cross_name_matrix` or in `avoid_list` with a one-liner.
- **The Cross-name rubric test**: the matrix uses the *same* dimensions across rows.
- **The Sector-lens test**: each ticker has a `sector-position` field (positive/neutral/negative) anchored in a sector-pack claim.

## Skipped calls

- For names in the universe but well below the shortlist cut, `forensic-accounting` is SKIPPED.
- `devils-advocate` SCAN runs on every name; STANDARD only on shortlist.

## Wallclock target

- Universe of 10 + 3 shortlisted: **15–25 minutes** all-free.
- Hybrid (free + Sonnet for synthesis): **10–15 minutes**.

## Cost target

| Universe | Cost target |
|----------|------------|
| 5 names + 3 shortlist | $0.10–$0.40 |
| 10 names + 5 shortlist | $0.30–$1.00 |

## Out of scope (f5)

- Investment universe generation (sourcing tickers). Use f6 for screening.
- Stock-picking without a sector frame. Use f1.
- Pure macro critique of the sector. Use f8.

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
