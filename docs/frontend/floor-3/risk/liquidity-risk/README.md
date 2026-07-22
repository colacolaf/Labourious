# Liquidity Risk Agent

> Floor 3 — Room 2: Risk
> Lead: Nassim Taleb

## Persona
— (unnamed utility agent)

### Role
Assesses position liquidity and market depth. Flags when a position is too large to exit cleanly and when market liquidity is deteriorating.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Bid-ask spreads, ADV, and depth data |

Set in `.env` or environment: `export POLYGON_API_KEY="your-key-here"`
