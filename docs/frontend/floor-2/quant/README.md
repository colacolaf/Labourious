# Quant (Room 4)

> Floor 2 — Analysis
> Lead: **Jim Simons**

Quant builds the models. Factor analysis, statistical arbitrage, volatility, momentum, machine learning, regime detection, risk budgeting — the mathematical engine of the firm.

## Agents

| Agent | File |
|-------|------|
| **Jim Simons** — Lead Quant | [`jim-simons/`](jim-simons/) |
| Factor Analysis Agent | [`factor-analysis/`](factor-analysis/) |
| **Ed Thorp** — Statistical Arbitrage Agent | [`statistical-arbitrage/`](statistical-arbitrage/) |
| Options & Volatility Agent | [`options-volatility/`](options-volatility/) |
| Momentum & Trend Agent | [`momentum-trend/`](momentum-trend/) |
| Machine Learning Agent | [`machine-learning/`](machine-learning/) |
| Regime Detection Agent | [`regime-detection/`](regime-detection/) |
| Risk Budgeting & Allocation Agent | [`risk-budgeting-allocation/`](risk-budgeting-allocation/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Historical price data, options chains, and market data for quant models |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
