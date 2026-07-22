# Consumer Spending Agent

> Ground Floor — Room 13: Alternative Data
> Lead: Matthew Granade

## Persona
— (unnamed utility agent)

### Role
Tracks credit card transaction data, receipt panels, foot traffic, and point-of-sale data. Reads the consumer economy in real time.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `SECOND_MEASURE_API_KEY` | Bloomberg Second Measure | Consumer transaction data — spending patterns by merchant, category, and demographic |

Set in `.env` or environment: `export SECOND_MEASURE_API_KEY="your-key-here"`
