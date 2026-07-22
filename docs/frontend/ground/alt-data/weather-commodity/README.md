# Weather & Commodity Agent

> Ground Floor — Room 13: Alternative Data
> Lead: Matthew Granade

## Persona
— (unnamed utility agent)

### Role
Monitors weather patterns, natural disasters, crop conditions, and commodity supply signals. Tracks how physical-world events ripple into markets.

## System Prompt
_TBD_

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `OPENWEATHER_API_KEY` | OpenWeatherMap | Current weather, forecasts, and historical weather patterns. Commodity prices via exchange APIs. |

Set in `.env` or environment: `export OPENWEATHER_API_KEY="your-key-here"`
