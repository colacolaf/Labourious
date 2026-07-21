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
- Room directories — individual agent profiles with persona, background, role, system prompt, and tool stubs
- `ui.md` — UI showcase and visual design (stub)

Plus the shared:
- [`lobby-template.md`](./lobby-template.md) — grid-based lobby layout reference

## Agent Index

### Ground Floor
| Agent | Room | File |
|-------|------|------|
| Entrance Bodyguard | Perimeter | [`ground/perimeter/entrance-bodyguard.md`](./ground/perimeter/entrance-bodyguard.md) |
| Web Research | Research (1) | [`ground/research/web-research.md`](./ground/research/web-research.md) |
| **John Hempton** — SEC/Regulatory | Research (1) | [`ground/research/sec-regulatory.md`](./ground/research/sec-regulatory.md) |
| Hedge Fund & Political Filings Intern | Research (1) | [`ground/research/hedge-fund-political-filings-intern.md`](./ground/research/hedge-fund-political-filings-intern.md) |
| Academic Research | Research (1) | [`ground/research/academic-research.md`](./ground/research/academic-research.md) |
| News Aggregation | Research (1) | [`ground/research/news-aggregation.md`](./ground/research/news-aggregation.md) |
| Data Scout | Research (1) | [`ground/research/data-scout.md`](./ground/research/data-scout.md) |
| News Sentiment | Sentiment (7) | [`ground/sentiment/news-sentiment.md`](./ground/sentiment/news-sentiment.md) |
| Social Media & Retail | Sentiment (7) | [`ground/sentiment/social-media-retail.md`](./ground/sentiment/social-media-retail.md) |
| Insider & Institutional | Sentiment (7) | [`ground/sentiment/insider-institutional.md`](./ground/sentiment/insider-institutional.md) |
| **Jon Najarian** — Options Flow & Dark Pool | Sentiment (7) | [`ground/sentiment/options-flow-dark-pool.md`](./ground/sentiment/options-flow-dark-pool.md) |
| Analyst & Earnings Revision | Sentiment (7) | [`ground/sentiment/analyst-earnings-revision.md`](./ground/sentiment/analyst-earnings-revision.md) |
| **James Crawford** — Satellite & Geospatial | Alt Data (13) | [`ground/alt-data/satellite-geospatial.md`](./ground/alt-data/satellite-geospatial.md) |
| Supply Chain | Alt Data (13) | [`ground/alt-data/supply-chain.md`](./ground/alt-data/supply-chain.md) |
| Consumer Spending | Alt Data (13) | [`ground/alt-data/consumer-spending.md`](./ground/alt-data/consumer-spending.md) |
| Weather & Commodity | Alt Data (13) | [`ground/alt-data/weather-commodity.md`](./ground/alt-data/weather-commodity.md) |
| Web & App Traffic | Alt Data (13) | [`ground/alt-data/web-app-traffic.md`](./ground/alt-data/web-app-traffic.md) |
| Storage | Storage (0) | [`ground/storage/storage.md`](./ground/storage/storage.md) |

### Floor 2
| Agent | Room | File |
|-------|------|------|
| Central Bank & Liquidity | Macro (3) | [`floor-2/macro/central-bank-liquidity.md`](./floor-2/macro/central-bank-liquidity.md) |
| **Ian Bremmer** — Geopolitical Risk | Macro (3) | [`floor-2/macro/geopolitical-risk.md`](./floor-2/macro/geopolitical-risk.md) |
| Currency & Sovereign Debt | Macro (3) | [`floor-2/macro/currency-sovereign-debt.md`](./floor-2/macro/currency-sovereign-debt.md) |
| Global Growth Tracker | Macro (3) | [`floor-2/macro/global-growth-tracker.md`](./floor-2/macro/global-growth-tracker.md) |
| Factor Analysis | Quant (4) | [`floor-2/quant/factor-analysis.md`](./floor-2/quant/factor-analysis.md) |
| **Ed Thorp** — Statistical Arbitrage | Quant (4) | [`floor-2/quant/statistical-arbitrage.md`](./floor-2/quant/statistical-arbitrage.md) |
| Options & Volatility | Quant (4) | [`floor-2/quant/options-volatility.md`](./floor-2/quant/options-volatility.md) |
| Momentum & Trend | Quant (4) | [`floor-2/quant/momentum-trend.md`](./floor-2/quant/momentum-trend.md) |
| Machine Learning | Quant (4) | [`floor-2/quant/machine-learning.md`](./floor-2/quant/machine-learning.md) |
| Regime Detection | Quant (4) | [`floor-2/quant/regime-detection.md`](./floor-2/quant/regime-detection.md) |
| Risk Budgeting & Allocation | Quant (4) | [`floor-2/quant/risk-budgeting-allocation.md`](./floor-2/quant/risk-budgeting-allocation.md) |
| DCF & Valuation | Fundamental (5) | [`floor-2/fundamental/dcf-valuation.md`](./floor-2/fundamental/dcf-valuation.md) |
| Moat & Competitive Analysis | Fundamental (5) | [`floor-2/fundamental/moat-competitive-analysis.md`](./floor-2/fundamental/moat-competitive-analysis.md) |
| Management Quality | Fundamental (5) | [`floor-2/fundamental/management-quality.md`](./floor-2/fundamental/management-quality.md) |
| **Harry Markopolos** — Forensic Accounting | Fundamental (5) | [`floor-2/fundamental/forensic-accounting.md`](./floor-2/fundamental/forensic-accounting.md) |
| Catalyst & Event | Fundamental (5) | [`floor-2/fundamental/catalyst-event.md`](./floor-2/fundamental/catalyst-event.md) |
| Industry Structure | Fundamental (5) | [`floor-2/fundamental/industry-structure.md`](./floor-2/fundamental/industry-structure.md) |
| Chart & Pattern | Technical (6) | [`floor-2/technical/chart-pattern.md`](./floor-2/technical/chart-pattern.md) |
| Volume & Order Flow | Technical (6) | [`floor-2/technical/volume-order-flow.md`](./floor-2/technical/volume-order-flow.md) |
| Market Microstructure | Technical (6) | [`floor-2/technical/market-microstructure.md`](./floor-2/technical/market-microstructure.md) |
| Technical Signal Engine | Technical (6) | [`floor-2/technical/technical-signal-engine.md`](./floor-2/technical/technical-signal-engine.md) |
| **Alex Svanevik** — On-Chain Analytics | Crypto (14) | [`floor-2/crypto/on-chain-analytics.md`](./floor-2/crypto/on-chain-analytics.md) |
| DeFi & Yield | Crypto (14) | [`floor-2/crypto/defi-yield.md`](./floor-2/crypto/defi-yield.md) |
| Tokenomics | Crypto (14) | [`floor-2/crypto/tokenomics.md`](./floor-2/crypto/tokenomics.md) |
| Protocol Risk | Crypto (14) | [`floor-2/crypto/protocol-risk.md`](./floor-2/crypto/protocol-risk.md) |

### Floor 3
| Agent | Room | File |
|-------|------|------|
| VaR & Stress Test | Risk (2) | [`floor-3/risk/var-stress-test.md`](./floor-3/risk/var-stress-test.md) |
| Correlation & Concentration | Risk (2) | [`floor-3/risk/correlation-concentration.md`](./floor-3/risk/correlation-concentration.md) |
| **Didier Sornette** — Black Swan Detection | Risk (2) | [`floor-3/risk/black-swan-detection.md`](./floor-3/risk/black-swan-detection.md) |
| Drawdown Monitor | Risk (2) | [`floor-3/risk/drawdown-monitor.md`](./floor-3/risk/drawdown-monitor.md) |
| Liquidity Risk | Risk (2) | [`floor-3/risk/liquidity-risk.md`](./floor-3/risk/liquidity-risk.md) |
| Factor Risk | Risk (2) | [`floor-3/risk/factor-risk.md`](./floor-3/risk/factor-risk.md) |
| **Meredith Whitney** — Devil's Advocate | Critique (11) | [`floor-3/critique/devils-advocate.md`](./floor-3/critique/devils-advocate.md) |
| Bear Case Intern | Critique (11) | [`floor-3/critique/bear-case-intern.md`](./floor-3/critique/bear-case-intern.md) |
| Blind Spot Detector | Critique (11) | [`floor-3/critique/blind-spot-detector.md`](./floor-3/critique/blind-spot-detector.md) |
| Historical Analog Intern | Critique (11) | [`floor-3/critique/historical-analog-intern.md`](./floor-3/critique/historical-analog-intern.md) |
| Assumption Challenger | Critique (11) | [`floor-3/critique/assumption-challenger.md`](./floor-3/critique/assumption-challenger.md) |
| Conflict Resolution | Critique (11) | [`floor-3/critique/conflict-resolution.md`](./floor-3/critique/conflict-resolution.md) |
| Regulatory Compliance | Compliance (12) | [`floor-3/compliance/regulatory-compliance.md`](./floor-3/compliance/regulatory-compliance.md) |
| **H. David Rosenbloom** — Cross-Border Tax | Compliance (12) | [`floor-3/compliance/cross-border-tax.md`](./floor-3/compliance/cross-border-tax.md) |
| Trading Restriction | Compliance (12) | [`floor-3/compliance/trading-restriction.md`](./floor-3/compliance/trading-restriction.md) |

### Floor 4
| Agent | Room | File |
|-------|------|------|
| **David Swensen** — Asset Allocation | Strategy (8) | [`floor-4/strategy/asset-allocation.md`](./floor-4/strategy/asset-allocation.md) |
| Tactical Overlay Intern | Strategy (8) | [`floor-4/strategy/tactical-overlay-intern.md`](./floor-4/strategy/tactical-overlay-intern.md) |
| Hedging & Protection | Strategy (8) | [`floor-4/strategy/hedging-protection.md`](./floor-4/strategy/hedging-protection.md) |
| Tax Optimization | Strategy (8) | [`floor-4/strategy/tax-optimization.md`](./floor-4/strategy/tax-optimization.md) |
| Portfolio Construction | Strategy (8) | [`floor-4/strategy/portfolio-construction.md`](./floor-4/strategy/portfolio-construction.md) |
| Position Sizing Intern | Strategy (8) | [`floor-4/strategy/position-sizing-intern.md`](./floor-4/strategy/position-sizing-intern.md) |
| Order Routing | Execution (9) | [`floor-4/execution/order-routing.md`](./floor-4/execution/order-routing.md) |
| Execution Algorithm | Execution (9) | [`floor-4/execution/execution-algorithm.md`](./floor-4/execution/execution-algorithm.md) |
| Timing & Slippage | Execution (9) | [`floor-4/execution/timing-slippage.md`](./floor-4/execution/timing-slippage.md) |
| Pre-Flight Check | Execution (9) | [`floor-4/execution/pre-flight-check.md`](./floor-4/execution/pre-flight-check.md) |
| Knowledge Graph | Memory (10) | [`floor-4/memory/knowledge-graph.md`](./floor-4/memory/knowledge-graph.md) |
| Learning & Reflection | Memory (10) | [`floor-4/memory/learning-reflection.md`](./floor-4/memory/learning-reflection.md) |
| Quality Control | Control (15) | [`floor-4/control/quality-control.md`](./floor-4/control/quality-control.md) |
| Agent Health Monitor | Control (15) | [`floor-4/control/agent-health-monitor.md`](./floor-4/control/agent-health-monitor.md) |
| Daily Briefing | Tasks (16) | [`floor-4/tasks/daily-briefing.md`](./floor-4/tasks/daily-briefing.md) |
| Opportunity Scout | Tasks (16) | [`floor-4/tasks/opportunity-scout.md`](./floor-4/tasks/opportunity-scout.md) |

### Penthouse
| Agent | File |
|-------|------|
| Portfolio Manager | [`penthouse/agents/portfolio-manager.md`](./penthouse/agents/portfolio-manager.md) |
| PM Bodyguard | [`penthouse/agents/pm-bodyguard.md`](./penthouse/agents/pm-bodyguard.md) |
