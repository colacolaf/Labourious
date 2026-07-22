# Execution (Room 9)

> Floor 4 — Command
> Lead: **Vlad Tenev**

Execution carries out the plan. Order routing, algorithms, timing optimization, and pre-flight checks — getting trades done without bleeding money.

## Agents

| Agent | File |
|-------|------|
| **Vlad Tenev** — Lead Execution | [`vlad-tenev/`](vlad-tenev/) |
| Order Routing Agent | [`order-routing/`](order-routing/) |
| Execution Algorithm Agent | [`execution-algorithm/`](execution-algorithm/) |
| Timing & Slippage Agent | [`timing-slippage/`](timing-slippage/) |
| Pre-Flight Check Agent | [`pre-flight-check/`](pre-flight-check/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `ALPACA_API_KEY` | Alpaca Markets | Order execution, position management, and market data — shared by all Execution room agents |
| `POLYGON_API_KEY` | Polygon.io | Real-time market data for timing, slippage, and execution quality analysis |

Set in `.env` or environment: `export ALPACA_API_KEY="your-key-here"`
