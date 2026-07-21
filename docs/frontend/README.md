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
- `README/` — floor overview, rooms table, and layout notes
- Room directories — individual agent profiles with persona, background, role, system prompt, and tool stubs
- `ui/` — UI showcase and visual design (stub)

Plus the shared:
- [`lobby-template.md`](./lobby-template.md) — grid-based lobby layout reference

## Agent Index

### Ground Floor
| Agent | Room | File |
|-------|------|------|
| Entrance Bodyguard Agent | Perimeter | [`ground/perimeter/entrance-bodyguard/`](./ground/perimeter/entrance-bodyguard/) |
| Web Research Agent | Research (1) | [`ground/research/web-research/`](./ground/research/web-research/) |
| **John Hempton** — SEC/Regulatory | Research (1) | [`ground/research/sec-regulatory/`](./ground/research/sec-regulatory/) |
| Hedge Fund & Political Filings Intern | Research (1) | [`ground/research/hedge-fund-political-filings-intern/`](./ground/research/hedge-fund-political-filings-intern/) |
| Academic Research Agent | Research (1) | [`ground/research/academic-research/`](./ground/research/academic-research/) |
| News Aggregation Agent | Research (1) | [`ground/research/news-aggregation/`](./ground/research/news-aggregation/) |
| Data Scout Agent | Research (1) | [`ground/research/data-scout/`](./ground/research/data-scout/) |
| News Sentiment Agent | Sentiment (7) | [`ground/sentiment/news-sentiment/`](./ground/sentiment/news-sentiment/) |
| Social Media & Retail Agent | Sentiment (7) | [`ground/sentiment/social-media-retail/`](./ground/sentiment/social-media-retail/) |
| Insider & Institutional Agent | Sentiment (7) | [`ground/sentiment/insider-institutional/`](./ground/sentiment/insider-institutional/) |
| **Jon Najarian** — Options Flow & Dark Pool | Sentiment (7) | [`ground/sentiment/options-flow-dark-pool/`](./ground/sentiment/options-flow-dark-pool/) |
| Analyst & Earnings Revision Agent | Sentiment (7) | [`ground/sentiment/analyst-earnings-revision/`](./ground/sentiment/analyst-earnings-revision/) |
| **James Crawford** — Satellite & Geospatial | Alt Data (13) | [`ground/alt-data/satellite-geospatial/`](./ground/alt-data/satellite-geospatial/) |
| Supply Chain Agent | Alt Data (13) | [`ground/alt-data/supply-chain/`](./ground/alt-data/supply-chain/) |
| Consumer Spending Agent | Alt Data (13) | [`ground/alt-data/consumer-spending/`](./ground/alt-data/consumer-spending/) |
| Weather & Commodity Agent | Alt Data (13) | [`ground/alt-data/weather-commodity/`](./ground/alt-data/weather-commodity/) |
| Web & App Traffic Agent | Alt Data (13) | [`ground/alt-data/web-app-traffic/`](./ground/alt-data/web-app-traffic/) |
| Storage Agent | Storage (0) | [`ground/storage/storage/`](./ground/storage/storage/) |

### Floor 2
| Agent | Room | File |
|-------|------|------|
| Central Bank & Liquidity Agent | Macro (3) | [`floor-2/macro/central-bank-liquidity/`](./floor-2/macro/central-bank-liquidity/) |
| **Ian Bremmer** — Geopolitical Risk | Macro (3) | [`floor-2/macro/geopolitical-risk/`](./floor-2/macro/geopolitical-risk/) |
| Currency & Sovereign Debt Agent | Macro (3) | [`floor-2/macro/currency-sovereign-debt/`](./floor-2/macro/currency-sovereign-debt/) |
| Global Growth Tracker Agent | Macro (3) | [`floor-2/macro/global-growth-tracker/`](./floor-2/macro/global-growth-tracker/) |
| Factor Analysis Agent | Quant (4) | [`floor-2/quant/factor-analysis/`](./floor-2/quant/factor-analysis/) |
| **Ed Thorp** — Statistical Arbitrage | Quant (4) | [`floor-2/quant/statistical-arbitrage/`](./floor-2/quant/statistical-arbitrage/) |
| Options & Volatility Agent | Quant (4) | [`floor-2/quant/options-volatility/`](./floor-2/quant/options-volatility/) |
| Momentum & Trend Agent | Quant (4) | [`floor-2/quant/momentum-trend/`](./floor-2/quant/momentum-trend/) |
| Machine Learning Agent | Quant (4) | [`floor-2/quant/machine-learning/`](./floor-2/quant/machine-learning/) |
| Regime Detection Agent | Quant (4) | [`floor-2/quant/regime-detection/`](./floor-2/quant/regime-detection/) |
| Risk Budgeting & Allocation Agent | Quant (4) | [`floor-2/quant/risk-budgeting-allocation/`](./floor-2/quant/risk-budgeting-allocation/) |
| DCF & Valuation Agent | Fundamental (5) | [`floor-2/fundamental/dcf-valuation/`](./floor-2/fundamental/dcf-valuation/) |
| Moat & Competitive Analysis Agent | Fundamental (5) | [`floor-2/fundamental/moat-competitive-analysis/`](./floor-2/fundamental/moat-competitive-analysis/) |
| Management Quality Agent | Fundamental (5) | [`floor-2/fundamental/management-quality/`](./floor-2/fundamental/management-quality/) |
| **Harry Markopolos** — Forensic Accounting | Fundamental (5) | [`floor-2/fundamental/forensic-accounting/`](./floor-2/fundamental/forensic-accounting/) |
| Catalyst & Event Agent | Fundamental (5) | [`floor-2/fundamental/catalyst-event/`](./floor-2/fundamental/catalyst-event/) |
| Industry Structure Agent | Fundamental (5) | [`floor-2/fundamental/industry-structure/`](./floor-2/fundamental/industry-structure/) |
| Chart & Pattern Agent | Technical (6) | [`floor-2/technical/chart-pattern/`](./floor-2/technical/chart-pattern/) |
| Volume & Order Flow Agent | Technical (6) | [`floor-2/technical/volume-order-flow/`](./floor-2/technical/volume-order-flow/) |
| Market Microstructure Agent | Technical (6) | [`floor-2/technical/market-microstructure/`](./floor-2/technical/market-microstructure/) |
| Technical Signal Engine Agent | Technical (6) | [`floor-2/technical/technical-signal-engine/`](./floor-2/technical/technical-signal-engine/) |
| **Alex Svanevik** — On-Chain Analytics | Crypto (14) | [`floor-2/crypto/on-chain-analytics/`](./floor-2/crypto/on-chain-analytics/) |
| DeFi & Yield Agent | Crypto (14) | [`floor-2/crypto/defi-yield/`](./floor-2/crypto/defi-yield/) |
| Tokenomics Agent | Crypto (14) | [`floor-2/crypto/tokenomics/`](./floor-2/crypto/tokenomics/) |
| Protocol Risk Agent | Crypto (14) | [`floor-2/crypto/protocol-risk/`](./floor-2/crypto/protocol-risk/) |

### Floor 3
| Agent | Room | File |
|-------|------|------|
| VaR & Stress Test Agent | Risk (2) | [`floor-3/risk/var-stress-test/`](./floor-3/risk/var-stress-test/) |
| Correlation & Concentration Agent | Risk (2) | [`floor-3/risk/correlation-concentration/`](./floor-3/risk/correlation-concentration/) |
| **Didier Sornette** — Black Swan Detection | Risk (2) | [`floor-3/risk/black-swan-detection/`](./floor-3/risk/black-swan-detection/) |
| Drawdown Monitor Agent | Risk (2) | [`floor-3/risk/drawdown-monitor/`](./floor-3/risk/drawdown-monitor/) |
| Liquidity Risk Agent | Risk (2) | [`floor-3/risk/liquidity-risk/`](./floor-3/risk/liquidity-risk/) |
| Factor Risk Agent | Risk (2) | [`floor-3/risk/factor-risk/`](./floor-3/risk/factor-risk/) |
| **Meredith Whitney** — Devil's Advocate | Critique (11) | [`floor-3/critique/devils-advocate/`](./floor-3/critique/devils-advocate/) |
| Bear Case Intern | Critique (11) | [`floor-3/critique/bear-case-intern/`](./floor-3/critique/bear-case-intern/) |
| Blind Spot Detector Agent | Critique (11) | [`floor-3/critique/blind-spot-detector/`](./floor-3/critique/blind-spot-detector/) |
| Historical Analog Intern | Critique (11) | [`floor-3/critique/historical-analog-intern/`](./floor-3/critique/historical-analog-intern/) |
| Assumption Challenger Agent | Critique (11) | [`floor-3/critique/assumption-challenger/`](./floor-3/critique/assumption-challenger/) |
| Conflict Resolution Agent | Critique (11) | [`floor-3/critique/conflict-resolution/`](./floor-3/critique/conflict-resolution/) |
| Regulatory Compliance Agent | Compliance (12) | [`floor-3/compliance/regulatory-compliance/`](./floor-3/compliance/regulatory-compliance/) |
| **H. David Rosenbloom** — Cross-Border Tax | Compliance (12) | [`floor-3/compliance/cross-border-tax/`](./floor-3/compliance/cross-border-tax/) |
| Trading Restriction Agent | Compliance (12) | [`floor-3/compliance/trading-restriction/`](./floor-3/compliance/trading-restriction/) |

### Floor 4
| Agent | Room | File |
|-------|------|------|
| **David Swensen** — Asset Allocation | Strategy (8) | [`floor-4/strategy/asset-allocation/`](./floor-4/strategy/asset-allocation/) |
| Tactical Overlay Intern | Strategy (8) | [`floor-4/strategy/tactical-overlay-intern/`](./floor-4/strategy/tactical-overlay-intern/) |
| Hedging & Protection Agent | Strategy (8) | [`floor-4/strategy/hedging-protection/`](./floor-4/strategy/hedging-protection/) |
| Tax Optimization Agent | Strategy (8) | [`floor-4/strategy/tax-optimization/`](./floor-4/strategy/tax-optimization/) |
| Portfolio Construction Agent | Strategy (8) | [`floor-4/strategy/portfolio-construction/`](./floor-4/strategy/portfolio-construction/) |
| Position Sizing Intern | Strategy (8) | [`floor-4/strategy/position-sizing-intern/`](./floor-4/strategy/position-sizing-intern/) |
| Order Routing Agent | Execution (9) | [`floor-4/execution/order-routing/`](./floor-4/execution/order-routing/) |
| Execution Algorithm Agent | Execution (9) | [`floor-4/execution/execution-algorithm/`](./floor-4/execution/execution-algorithm/) |
| Timing & Slippage Agent | Execution (9) | [`floor-4/execution/timing-slippage/`](./floor-4/execution/timing-slippage/) |
| Pre-Flight Check Agent | Execution (9) | [`floor-4/execution/pre-flight-check/`](./floor-4/execution/pre-flight-check/) |
| Knowledge Graph Agent | Memory (10) | [`floor-4/memory/knowledge-graph/`](./floor-4/memory/knowledge-graph/) |
| Learning & Reflection Agent | Memory (10) | [`floor-4/memory/learning-reflection/`](./floor-4/memory/learning-reflection/) |
| Quality Control Agent | Control (15) | [`floor-4/control/quality-control/`](./floor-4/control/quality-control/) |
| Agent Health Monitor | Control (15) | [`floor-4/control/agent-health-monitor/`](./floor-4/control/agent-health-monitor/) |
| Daily Briefing Agent | Tasks (16) | [`floor-4/tasks/daily-briefing/`](./floor-4/tasks/daily-briefing/) |
| Opportunity Scout Agent | Tasks (16) | [`floor-4/tasks/opportunity-scout/`](./floor-4/tasks/opportunity-scout/) |

### Penthouse
| Agent | File |
|-------|------|
| Portfolio Manager | [`penthouse/agents/portfolio-manager/`](./penthouse/agents/portfolio-manager/) |
| PM Bodyguard | [`penthouse/agents/pm-bodyguard/`](./penthouse/agents/pm-bodyguard/) |
