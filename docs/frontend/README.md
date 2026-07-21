# Frontend — Labourious HQ

Five floors. One elevator. The Portfolio Manager at the top.

## Elevator Teleport

Walk to the elevator shaft, click a floor button, doors close — brief flicker/hum — doors open on the new floor. Takes roughly one second. Wall panel beside the elevator shows which agents are active on each floor.

## Floors

| Floor | Name | Directory | Rooms |
|-------|------|-----------|-------|
| Ground | Intake | [`ground/`](./ground/) | Entrance Bodyguard, Research (1), Sentiment (7), Alternative Data (13), Storage (0) |
| Floor 2 | Analysis | [`floor-2/`](./floor-2/) | Macro (3), Quant (4), Fundamental (5), Technical (6), Crypto (14) |
| Floor 3 | Judgment | [`floor-3/`](./floor-3/) | Risk (2), Critique (11), Compliance & Tax (12) |
| Floor 4 | Command | [`floor-4/`](./floor-4/) | Strategy (8), Execution (9), Memory (10), Control (15), Tasks (16) |
| Penthouse | The Top | [`penthouse/`](./penthouse/) | Portfolio Manager, PM Bodyguard |

## Architecture

Each floor directory contains:
- `README.md` — floor overview, rooms table, and layout notes
- `agents/` — individual agent profiles with persona, background, role, system prompt, and tool stubs
- `ui.md` — UI showcase and visual design (stub)

Plus the shared:
- [`lobby-template.md`](./lobby-template.md) — grid-based lobby layout reference

## Agent Index

### Ground Floor
| Agent | Room | File |
|-------|------|------|
| Entrance Bodyguard | Perimeter | [`ground/agents/entrance-bodyguard.md`](./ground/agents/entrance-bodyguard.md) |
| Web Research | Research (1) | [`ground/agents/web-research.md`](./ground/agents/web-research.md) |
| **John Hempton** — SEC/Regulatory | Research (1) | [`ground/agents/sec-regulatory.md`](./ground/agents/sec-regulatory.md) |
| Hedge Fund & Political Filings Intern | Research (1) | [`ground/agents/hedge-fund-political-filings-intern.md`](./ground/agents/hedge-fund-political-filings-intern.md) |
| Academic Research | Research (1) | [`ground/agents/academic-research.md`](./ground/agents/academic-research.md) |
| News Aggregation | Research (1) | [`ground/agents/news-aggregation.md`](./ground/agents/news-aggregation.md) |
| Data Scout | Research (1) | [`ground/agents/data-scout.md`](./ground/agents/data-scout.md) |
| News Sentiment | Sentiment (7) | [`ground/agents/news-sentiment.md`](./ground/agents/news-sentiment.md) |
| Social Media & Retail | Sentiment (7) | [`ground/agents/social-media-retail.md`](./ground/agents/social-media-retail.md) |
| Insider & Institutional | Sentiment (7) | [`ground/agents/insider-institutional.md`](./ground/agents/insider-institutional.md) |
| **Jon Najarian** — Options Flow & Dark Pool | Sentiment (7) | [`ground/agents/options-flow-dark-pool.md`](./ground/agents/options-flow-dark-pool.md) |
| Analyst & Earnings Revision | Sentiment (7) | [`ground/agents/analyst-earnings-revision.md`](./ground/agents/analyst-earnings-revision.md) |
| **James Crawford** — Satellite & Geospatial | Alt Data (13) | [`ground/agents/satellite-geospatial.md`](./ground/agents/satellite-geospatial.md) |
| Supply Chain | Alt Data (13) | [`ground/agents/supply-chain.md`](./ground/agents/supply-chain.md) |
| Consumer Spending | Alt Data (13) | [`ground/agents/consumer-spending.md`](./ground/agents/consumer-spending.md) |
| Weather & Commodity | Alt Data (13) | [`ground/agents/weather-commodity.md`](./ground/agents/weather-commodity.md) |
| Web & App Traffic | Alt Data (13) | [`ground/agents/web-app-traffic.md`](./ground/agents/web-app-traffic.md) |
| Storage | Storage (0) | [`ground/agents/storage.md`](./ground/agents/storage.md) |

### Floor 2
| Agent | Room | File |
|-------|------|------|
| Central Bank & Liquidity | Macro (3) | [`floor-2/agents/central-bank-liquidity.md`](./floor-2/agents/central-bank-liquidity.md) |
| **Ian Bremmer** — Geopolitical Risk | Macro (3) | [`floor-2/agents/geopolitical-risk.md`](./floor-2/agents/geopolitical-risk.md) |
| Currency & Sovereign Debt | Macro (3) | [`floor-2/agents/currency-sovereign-debt.md`](./floor-2/agents/currency-sovereign-debt.md) |
| Global Growth Tracker | Macro (3) | [`floor-2/agents/global-growth-tracker.md`](./floor-2/agents/global-growth-tracker.md) |
| Factor Analysis | Quant (4) | [`floor-2/agents/factor-analysis.md`](./floor-2/agents/factor-analysis.md) |
| **Ed Thorp** — Statistical Arbitrage | Quant (4) | [`floor-2/agents/statistical-arbitrage.md`](./floor-2/agents/statistical-arbitrage.md) |
| Options & Volatility | Quant (4) | [`floor-2/agents/options-volatility.md`](./floor-2/agents/options-volatility.md) |
| Momentum & Trend | Quant (4) | [`floor-2/agents/momentum-trend.md`](./floor-2/agents/momentum-trend.md) |
| Machine Learning | Quant (4) | [`floor-2/agents/machine-learning.md`](./floor-2/agents/machine-learning.md) |
| Regime Detection | Quant (4) | [`floor-2/agents/regime-detection.md`](./floor-2/agents/regime-detection.md) |
| Risk Budgeting & Allocation | Quant (4) | [`floor-2/agents/risk-budgeting-allocation.md`](./floor-2/agents/risk-budgeting-allocation.md) |
| DCF & Valuation | Fundamental (5) | [`floor-2/agents/dcf-valuation.md`](./floor-2/agents/dcf-valuation.md) |
| Moat & Competitive Analysis | Fundamental (5) | [`floor-2/agents/moat-competitive-analysis.md`](./floor-2/agents/moat-competitive-analysis.md) |
| Management Quality | Fundamental (5) | [`floor-2/agents/management-quality.md`](./floor-2/agents/management-quality.md) |
| **Harry Markopolos** — Forensic Accounting | Fundamental (5) | [`floor-2/agents/forensic-accounting.md`](./floor-2/agents/forensic-accounting.md) |
| Catalyst & Event | Fundamental (5) | [`floor-2/agents/catalyst-event.md`](./floor-2/agents/catalyst-event.md) |
| Industry Structure | Fundamental (5) | [`floor-2/agents/industry-structure.md`](./floor-2/agents/industry-structure.md) |
| Chart & Pattern | Technical (6) | [`floor-2/agents/chart-pattern.md`](./floor-2/agents/chart-pattern.md) |
| Volume & Order Flow | Technical (6) | [`floor-2/agents/volume-order-flow.md`](./floor-2/agents/volume-order-flow.md) |
| Market Microstructure | Technical (6) | [`floor-2/agents/market-microstructure.md`](./floor-2/agents/market-microstructure.md) |
| Technical Signal Engine | Technical (6) | [`floor-2/agents/technical-signal-engine.md`](./floor-2/agents/technical-signal-engine.md) |
| **Alex Svanevik** — On-Chain Analytics | Crypto (14) | [`floor-2/agents/on-chain-analytics.md`](./floor-2/agents/on-chain-analytics.md) |
| DeFi & Yield | Crypto (14) | [`floor-2/agents/defi-yield.md`](./floor-2/agents/defi-yield.md) |
| Tokenomics | Crypto (14) | [`floor-2/agents/tokenomics.md`](./floor-2/agents/tokenomics.md) |
| Protocol Risk | Crypto (14) | [`floor-2/agents/protocol-risk.md`](./floor-2/agents/protocol-risk.md) |

### Floor 3
| Agent | Room | File |
|-------|------|------|
| VaR & Stress Test | Risk (2) | [`floor-3/agents/var-stress-test.md`](./floor-3/agents/var-stress-test.md) |
| Correlation & Concentration | Risk (2) | [`floor-3/agents/correlation-concentration.md`](./floor-3/agents/correlation-concentration.md) |
| **Didier Sornette** — Black Swan Detection | Risk (2) | [`floor-3/agents/black-swan-detection.md`](./floor-3/agents/black-swan-detection.md) |
| Drawdown Monitor | Risk (2) | [`floor-3/agents/drawdown-monitor.md`](./floor-3/agents/drawdown-monitor.md) |
| Liquidity Risk | Risk (2) | [`floor-3/agents/liquidity-risk.md`](./floor-3/agents/liquidity-risk.md) |
| Factor Risk | Risk (2) | [`floor-3/agents/factor-risk.md`](./floor-3/agents/factor-risk.md) |
| **Meredith Whitney** — Devil's Advocate | Critique (11) | [`floor-3/agents/devils-advocate.md`](./floor-3/agents/devils-advocate.md) |
| Bear Case Intern | Critique (11) | [`floor-3/agents/bear-case-intern.md`](./floor-3/agents/bear-case-intern.md) |
| Blind Spot Detector | Critique (11) | [`floor-3/agents/blind-spot-detector.md`](./floor-3/agents/blind-spot-detector.md) |
| Historical Analog Intern | Critique (11) | [`floor-3/agents/historical-analog-intern.md`](./floor-3/agents/historical-analog-intern.md) |
| Assumption Challenger | Critique (11) | [`floor-3/agents/assumption-challenger.md`](./floor-3/agents/assumption-challenger.md) |
| Conflict Resolution | Critique (11) | [`floor-3/agents/conflict-resolution.md`](./floor-3/agents/conflict-resolution.md) |
| Regulatory Compliance | Compliance (12) | [`floor-3/agents/regulatory-compliance.md`](./floor-3/agents/regulatory-compliance.md) |
| **H. David Rosenbloom** — Cross-Border Tax | Compliance (12) | [`floor-3/agents/cross-border-tax.md`](./floor-3/agents/cross-border-tax.md) |
| Trading Restriction | Compliance (12) | [`floor-3/agents/trading-restriction.md`](./floor-3/agents/trading-restriction.md) |

### Floor 4
| Agent | Room | File |
|-------|------|------|
| **David Swensen** — Asset Allocation | Strategy (8) | [`floor-4/agents/asset-allocation.md`](./floor-4/agents/asset-allocation.md) |
| Tactical Overlay Intern | Strategy (8) | [`floor-4/agents/tactical-overlay-intern.md`](./floor-4/agents/tactical-overlay-intern.md) |
| Hedging & Protection | Strategy (8) | [`floor-4/agents/hedging-protection.md`](./floor-4/agents/hedging-protection.md) |
| Tax Optimization | Strategy (8) | [`floor-4/agents/tax-optimization.md`](./floor-4/agents/tax-optimization.md) |
| Portfolio Construction | Strategy (8) | [`floor-4/agents/portfolio-construction.md`](./floor-4/agents/portfolio-construction.md) |
| Position Sizing Intern | Strategy (8) | [`floor-4/agents/position-sizing-intern.md`](./floor-4/agents/position-sizing-intern.md) |
| Order Routing | Execution (9) | [`floor-4/agents/order-routing.md`](./floor-4/agents/order-routing.md) |
| Execution Algorithm | Execution (9) | [`floor-4/agents/execution-algorithm.md`](./floor-4/agents/execution-algorithm.md) |
| Timing & Slippage | Execution (9) | [`floor-4/agents/timing-slippage.md`](./floor-4/agents/timing-slippage.md) |
| Pre-Flight Check | Execution (9) | [`floor-4/agents/pre-flight-check.md`](./floor-4/agents/pre-flight-check.md) |
| Knowledge Graph | Memory (10) | [`floor-4/agents/knowledge-graph.md`](./floor-4/agents/knowledge-graph.md) |
| Learning & Reflection | Memory (10) | [`floor-4/agents/learning-reflection.md`](./floor-4/agents/learning-reflection.md) |
| Quality Control | Control (15) | [`floor-4/agents/quality-control.md`](./floor-4/agents/quality-control.md) |
| Agent Health Monitor | Control (15) | [`floor-4/agents/agent-health-monitor.md`](./floor-4/agents/agent-health-monitor.md) |
| Daily Briefing | Tasks (16) | [`floor-4/agents/daily-briefing.md`](./floor-4/agents/daily-briefing.md) |
| Opportunity Scout | Tasks (16) | [`floor-4/agents/opportunity-scout.md`](./floor-4/agents/opportunity-scout.md) |

### Penthouse
| Agent | File |
|-------|------|
| Portfolio Manager | [`penthouse/agents/portfolio-manager.md`](./penthouse/agents/portfolio-manager.md) |
| PM Bodyguard | [`penthouse/agents/pm-bodyguard.md`](./penthouse/agents/pm-bodyguard.md) |
