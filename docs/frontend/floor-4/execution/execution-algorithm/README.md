# Execution Algorithm Agent

> Floor 4 — Room 9: Execution
> Lead: Vlad Tenev

## Persona
— (unnamed utility agent)

### Role
Runs execution algorithms — VWAP, TWAP, implementation shortfall, adaptive algos. Minimizes market impact and slippage on every trade.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `ALPACA_API_KEY` | Alpaca Markets | Real-time market data for algorithmic execution parameters |

Set in `.env` or environment: `export ALPACA_API_KEY="your-key-here"`
