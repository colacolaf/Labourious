# Pre-Flight Check Agent

> Floor 4 — Room 9: Execution
> Lead: Vlad Tenev

## Persona
— (unnamed utility agent)

### Role
Runs a final checklist before any trade executes — position limits, compliance checks, risk limits, cash availability, counterparty exposure. The last gate before orders hit the market.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `ALPACA_API_KEY` | Alpaca Markets | Current positions, buying power, and compliance status |

Set in `.env` or environment: `export ALPACA_API_KEY="your-key-here"`
