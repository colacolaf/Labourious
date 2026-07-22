# Macro (Room 3)

> Floor 2 — Analysis
> Lead: **Larry Fink**

Macro watches the global stage. Central banks, geopolitics, currencies, sovereign debt, and global growth — the big picture that drives everything else.

## Agents

| Agent | File |
|-------|------|
| **Larry Fink** — Lead Macro | [`larry-fink/`](larry-fink/) |
| Central Bank & Liquidity Agent | [`central-bank-liquidity/`](central-bank-liquidity/) |
| **Ian Bremmer** — Geopolitical Risk Agent | [`geopolitical-risk/`](geopolitical-risk/) |
| Currency & Sovereign Debt Agent | [`currency-sovereign-debt/`](currency-sovereign-debt/) |
| Global Growth Tracker Agent | [`global-growth-tracker/`](global-growth-tracker/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `FRED_API_KEY` | FRED (Federal Reserve) | Interest rates, balance sheet data, PMI composites, GDP growth |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
