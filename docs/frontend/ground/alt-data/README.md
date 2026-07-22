# Alternative Data (Room 13)

> Ground Floor — Intake
> Lead: **Matthew Granade**

Alternative Data finds signals nobody else is looking at. Satellites, supply chains, consumer receipts, weather patterns, web traffic — the unconventional intelligence that delivers an edge.

## Agents

| Agent | File |
|-------|------|
| **Matthew Granade** — Lead Alt Data | [`matthew-granade/`](matthew-granade/) |
| **James Crawford** — Satellite & Geospatial Agent | [`satellite-geospatial/`](satellite-geospatial/) |
| Supply Chain Agent | [`supply-chain/`](supply-chain/) |
| Consumer Spending Agent | [`consumer-spending/`](consumer-spending/) |
| Weather & Commodity Agent | [`weather-commodity/`](weather-commodity/) |
| Web & App Traffic Agent | [`web-app-traffic/`](web-app-traffic/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `PLANET_API_KEY` | Planet Labs | Satellite imagery for parking lot counts, tanker tracking, crop yields |
| `OPENWEATHER_API_KEY` | OpenWeatherMap | Current weather, forecasts, and commodity-impacting patterns |
| `SECOND_MEASURE_API_KEY` | Bloomberg Second Measure | Consumer transaction data by merchant, category, demographic |
| `SIMILARWEB_API_KEY` | SimilarWeb | Website and app traffic estimates and engagement metrics |
| `PANJIVA_API_KEY` | Panjiva / S&P Global | Trade data — bills of lading, import/export volumes, supplier relationships |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
