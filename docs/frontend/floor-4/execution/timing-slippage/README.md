# Timing & Slippage Agent

> Floor 4 — Room 9: Execution
> Lead: Vlad Tenev

## Persona
— (unnamed utility agent)

### Role
Analyzes optimal trade timing to minimize slippage. Monitors intraday liquidity patterns, spread dynamics, and market impact costs.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Historical slippage data by time-of-day buckets |

Set in `.env` or environment: `export POLYGON_API_KEY="your-key-here"`
