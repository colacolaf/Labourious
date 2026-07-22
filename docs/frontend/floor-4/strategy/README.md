# Strategy (Room 8)

> Floor 4 — Command
> Lead: **Ray Dalio**

Strategy builds the plan. Asset allocation, hedging, tax optimization, and portfolio construction — the room that decides where capital goes and why.

## Agents

| Agent | File |
|-------|------|
| **Ray Dalio** — Lead Strategy | [`ray-dalio/`](ray-dalio/) |
| **David Swensen** — Asset Allocation Agent | [`asset-allocation/`](asset-allocation/) |
| Tactical Overlay Intern | [`tactical-overlay-intern/`](tactical-overlay-intern/) |
| Hedging & Protection Agent | [`hedging-protection/`](hedging-protection/) |
| Tax Optimization Agent | [`tax-optimization/`](tax-optimization/) |
| Portfolio Construction Agent | [`portfolio-construction/`](portfolio-construction/) |
| Position Sizing Intern | [`position-sizing-intern/`](position-sizing-intern/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Options chain and market data for hedging, portfolio construction, and tax optimization |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
