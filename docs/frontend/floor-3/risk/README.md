# Risk (Room 2)

> Floor 3 — Judgment
> Lead: **Nassim Taleb**

Risk stress-tests the numbers. VaR models, correlation matrices, black swan detection, drawdown limits, liquidity checks — making sure the portfolio survives what the models didn't predict.

## Agents

| Agent | File |
|-------|------|
| **Nassim Taleb** — Lead Risk | [`nassim-taleb/`](nassim-taleb/) |
| VaR & Stress Test Agent | [`var-stress-test/`](var-stress-test/) |
| Correlation & Concentration Agent | [`correlation-concentration/`](correlation-concentration/) |
| **Didier Sornette** — Black Swan Detection Agent | [`black-swan-detection/`](black-swan-detection/) |
| Drawdown Monitor Agent | [`drawdown-monitor/`](drawdown-monitor/) |
| Liquidity Risk Agent | [`liquidity-risk/`](liquidity-risk/) |
| Factor Risk Agent | [`factor-risk/`](factor-risk/) |

## Tools

### API Keys

| Variable | Service | Purpose |
|----------|---------|---------|
| `POLYGON_API_KEY` | Polygon.io | Historical price and options data for VaR, correlation, and stress testing |

Set in `.env` or environment: `export VARIABLE="your-key-here"`
