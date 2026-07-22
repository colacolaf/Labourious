# Technical (Room 6)

> Floor 2 — Analysis
> Lead: **Mark Minervini**

Technical studies the charts. Pattern recognition, volume analysis, market microstructure, and systematic technical signals — the price action tells a story.

## Agents

| Agent | File |
|-------|------|
| **Mark Minervini** — Lead Technical | [`mark-minervini/`](mark-minervini/) |
| Chart & Pattern Agent | [`chart-pattern/`](chart-pattern/) |
| Volume & Order Flow Agent | [`volume-order-flow/`](volume-order-flow/) |
| Market Microstructure Agent | [`market-microstructure/`](market-microstructure/) |
| Technical Signal Engine Agent | [`technical-signal-engine/`](technical-signal-engine/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Real-time and historical price data for chart patterns, volume, and technical signals |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
