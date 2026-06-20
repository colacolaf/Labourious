---
name: phase3-frontend-design-choices
description: Frozen Phase 3.0 frontend design choices — all implementation tasks in Phase 3A/3B reference this file
metadata:
  type: project
  phase: 3.0
  status: frozen
  date: 2026-06-19
---

# Phase 3.0 — Frontend Design Choices (Frozen)

All choices made interactively via visual companion browser session on 2026-06-19.
**Do not change without re-running Phase 3.0 design review.**

---

## Choice 1 — Analytics Page Layout

**Selected: B — Single Scroll**

All sections stacked on one page in this order:
1. Portfolio Performance header (time range selector: 30d / YTD / ALL)
2. Equity curve (Recharts LineChart, full width)
3. KPI stat row: Return % · Sharpe · Max DD · Win Rate
4. Agent Leaderboard (sortable table with inline bar)
5. Correlation Matrix
6. Attribution — Today
7. Backtest Runner (inline, see Choice 4)

**Color note:** Use retro-professional palette (`var(--color-primary)` teal, `var(--color-secondary)` cyan, `var(--color-accent)` amber, `var(--status-success)` green, `var(--status-danger)` red). No hacker-green. Matches existing warroom theme.

---

## Choice 2 — Correlation Matrix Style

**Selected: B — Numbers table only**

- Plain table, zebra rows (`--bg-secondary` / `--bg-primary` alternating)
- Columns and rows = agent names
- Diagonal cells show `—` (self-correlation)
- All values formatted to 2 decimal places
- Cells with correlation > 0.7: amber `⚠` flag + `var(--color-accent)` text color
- Header: `CORRELATION — LAST 30D DAILY RETURNS`
- No color heatmap, no gradients on cells — values speak for themselves

---

## Choice 3 — Attribution Chart Style

**Selected: A — Waterfall chart**

- Recharts BarChart waterfall variant
- X-axis: agent names + Start/End markers
- Y-axis: cumulative P&L ($)
- Positive bars: `var(--color-primary)` teal fill
- Negative bars: `var(--status-danger)` red fill
- Start/End markers: amber vertical lines with label
- Title: `P&L ATTRIBUTION — {date}`
- Date picker to select which day to inspect (default: today)

---

## Choice 4 — Backtest Runner Placement

**Selected: A — Inline panel within Analytics page**

- Lives at bottom of Analytics scroll page as its own section
- Form: Agent dropdown · From date · To date · Mode (Basic / Walk-Forward radio)
- `▶ RUN BACKTEST` button triggers POST `/api/backtest/run`, polls for completion
- Results render inline below form:
  - KPI row: Return · Win% · Sharpe · Max DD
  - Equity curve chart (Recharts LineChart)
  - Trade log table (filterable, paginated)
  - `EXPORT CSV` button
- Loading state: spinner + "Running backtest…" while polling
- Error state: inline red error message (no modal)

---

## Choice 5 — Typography

**Selected: A — JetBrains Mono (keep existing)**

- No font file changes needed
- `--font-mono: 'JetBrains Mono', 'IBM Plex Mono', monospace` — unchanged
- Rationale: already installed, zero friction, excellent terminal legibility at small sizes

---

## Summary Table

| # | Decision | Choice |
|---|---|---|
| 1 | Analytics page layout | B — Single scroll |
| 2 | Correlation matrix style | B — Numbers table |
| 3 | Attribution chart | A — Waterfall |
| 4 | Backtest runner | A — Inline in Analytics |
| 5 | Typography | A — JetBrains Mono (no change) |

---

## Color System (applies to all Phase 3 components)

Inherit entirely from existing `frontend/src/styles/index.css` CSS variables:

```css
--bg-primary: #1a1a1a
--bg-secondary: #242424
--color-primary: #2d5a5a      /* teal — primary chart color */
--color-secondary: #4a9ede    /* cyan — accent/headers */
--color-accent: #FF8C42       /* amber — warnings, highlights */
--status-success: #4CAF50     /* green — positive P&L */
--status-danger: #f44336      /* red — negative P&L */
--text-primary: #e8dcc8       /* warm off-white — NOT pure #e8e8e8 */
--font-mono: 'JetBrains Mono', 'IBM Plex Mono', monospace
```

> **Note on `--text-primary`:** User specified warmer, more professional palette.
> Use `#e8dcc8` (warm cream) over `#e8e8e8` (cool grey) for body text in Phase 3 components.
> Update `index.css` variable as part of Phase 3A task 1.

---

*This file is the single source of truth for all Phase 3 visual decisions.*
*Phase 3A and 3B implementation tasks must reference this file, not re-derive choices.*
