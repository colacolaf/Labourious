# Thesis Register — durable memory across runs

> The thesis register gives the system **memory**. Without it, every analysis is one-shot; with it, every f1 run gets *better* by reading the last time the system thought about this name.

## What it solves

When the user runs `f1 NVDA` today and again next week, the second run should know:
- What was the prior thesis?
- What was the fragile assumption?
- Was it confirmed, shifted, or broken by what changed?
- What catalysts were on the watchlist?

**Today:** `python register.py show NVDA` prints the prior theses + updates + catalysts.

**Tomorrow:** registered f1 runs surface "what changed" automatically in the memo, so the user sees how the system's view evolved over time.

## Schema (SQLite)

Three tables — see `schema.sql`:

```sql
CREATE TABLE theses (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  date TEXT NOT NULL,
  thesis_text TEXT NOT NULL,
  conviction INTEGER NOT NULL,         -- 1..5
  bottom_line TEXT NOT NULL,           -- JSON: {direction, conviction, flip_trigger}
  evidence_urls TEXT NOT NULL,         -- JSON array
  flow_id TEXT NOT NULL,
  version INTEGER NOT NULL,            -- monotonically increasing per (ticker, flow_id)
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE updates (
  id INTEGER PRIMARY KEY,
  thesis_id INTEGER NOT NULL REFERENCES theses(id),
  date TEXT NOT NULL,
  what_changed TEXT NOT NULL,
  new_thesis_text TEXT,
  deltas TEXT,                         -- JSON: the things that flipped
  reason TEXT
);

CREATE TABLE catalysts (
  id INTEGER PRIMARY KEY,
  ticker TEXT NOT NULL,
  event TEXT NOT NULL,
  expected_date TEXT,
  what_to_watch TEXT,
  resolved_date TEXT,
  resolved_outcome TEXT
);
```

The DB lives at `docs/runtime/thesis_register/theses.db` by default. Override with `--db PATH` on `register.py` or via env `THESIS_REGISTER_DB`.

## API (`register.py`)

| Function | Purpose |
|----------|---------|
| `read_thesis(ticker, since_days=None)` | Returns the latest thesis (or all since cutoff) |
| `diff_thesis(ticker, new_thesis_text)` | Returns changed fields vs latest |
| `write_thesis(ticker, thesis_text, conviction, bottom_line, evidence_urls, flow_id)` | Append a new versioned row |
| `add_update(ticker, what_changed, ...)` | Record what flipped since last run |
| `add_catalyst(ticker, event, expected_date, what_to_watch)` | Add a watchlist item |
| `resolve_catalyst(id, resolved_date, outcome)` | Mark a catalyst resolved |

## CLI

```bash
# Read
python register.py show NVDA
python register.py catalysts AAPL
python register.py show NVDA --since 30

# Write
python register.py write NVDA --thesis "Wide moat; 22% above base." --conviction 4 \
    --bottom-line '{"direction":"HOLD","flip_trigger":"$720"}' --flow f1
python register.py update NVDA --changed "M-Score worsened to -0.85" --reason "Q3 10-Q"
python register.py add-catalyst NVDA --event "Q4 2026 earnings" --expected 2026-11-20 --watch "channel inventory margin"
python register.py resolve-catalyst <id> --date 2026-11-20 --outcome "Channel inventory margin held; thesis stands."
```

## When flows write to it

Every flow that produces a thesis_or_update writes to the register on success:

| Flow | Writes | Updates? |
|------|--------|----------|
| f1 (analyze) | new `theses` row | sometimes (a Catalyst) |
| f2 (compare) | new `theses` row per ranked pick | no |
| f3 (preview) | new `theses` row (lightweight) | adds catalysts |
| f4 (review) | new `theses` row + an `updates` row + resolves catalysts | yes (core use case) |
| f5 (sector) | new `theses` row per shortlisted ticker | no |
| f6 (screen) | new `theses` row per shortlisted ticker | no |
| f7 (event) | new `theses` row (timestamped) + add an event catalyst | sometimes |
| f8 (overlay) | new `theses` row per overlaid thesis + an `updates` row marking the macro | yes |

A failure mid-flow does **not** write. The user can re-run.

## Why this matters

Without the register, **the system has no compounding**. Every flow is stateless. **It's the single most important runnable feature after the runtime itself** — because it's what makes analysis "the team you'd hire if you could afford one" *instead of* the team that re-learns everything every Monday.

See [`../../ROADMAP.md`](../../ROADMAP.md) P0 item 6 — this ships in tandem with the first f1 acceptance.
