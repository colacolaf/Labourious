# Agent Prompt Library

**89 system prompts** — the raw material for the app's agent roster. Every agent folder contains a `system-prompt.md` and a `README.md` (persona, role, tools, API keys).

> **Note on paths:** the physical folders still carry the old building names (`ground/`, `floor-2/`… `penthouse/`). The building concept is gone — these are now just category groupings, and the tree will be reorganized (e.g. `prompts/categories/<category>/<agent>/`) during the skeleton build. **Do not treat floor names as product meaning.**

## Category → Folder Map

| Category | Folder |
|----------|--------|
| Research (1) | [`ground/research/`](ground/research/) |
| Perimeter | [`ground/perimeter/`](ground/perimeter/) |
| Sentiment (7) | [`ground/sentiment/`](ground/sentiment/) |
| Alternative Data (13) | [`ground/alt-data/`](ground/alt-data/) |
| Storage | [`ground/storage/`](ground/storage/) |
| Macro (3) | [`floor-2/macro/`](floor-2/macro/) |
| Quant (4) | [`floor-2/quant/`](floor-2/quant/) |
| Fundamental (5) | [`floor-2/fundamental/`](floor-2/fundamental/) |
| Technical (6) | [`floor-2/technical/`](floor-2/technical/) |
| Crypto/Digital Assets (14) | [`floor-2/crypto/`](floor-2/crypto/) |
| Risk (2) | [`floor-3/risk/`](floor-3/risk/) |
| Critique (11) | [`floor-3/critique/`](floor-3/critique/) |
| Compliance & Tax (12) | [`floor-3/compliance/`](floor-3/compliance/) |
| Strategy (8) | [`floor-4/strategy/`](floor-4/strategy/) |
| Execution (9) | [`floor-4/execution/`](floor-4/execution/) |
| Memory (10) | [`floor-4/memory/`](floor-4/memory/) |
| Control (15) | [`floor-4/control/`](floor-4/control/) |
| Tasks (16) | [`floor-4/tasks/`](floor-4/tasks/) |
| Penthouse (orchestrator-era) | [`penthouse/`](penthouse/) |

## Agent Index

### Research (1) — Ground
| Agent | Folder | Prompt |
|-------|--------|--------|
| Michael Burry — Lead | [`ground/research/michael-burry/`](ground/research/michael-burry/) | ✅ |
| Web Research Agent | [`ground/research/web-research/`](ground/research/web-research/) | ✅ |
| John Hempton — SEC/Regulatory | [`ground/research/sec-regulatory/`](ground/research/sec-regulatory/) | ✅ |
| Hedge Fund & Political Filings Intern | [`ground/research/hedge-fund-political-filings-intern/`](ground/research/hedge-fund-political-filings-intern/) | ✅ |
| Academic Research Agent | [`ground/research/academic-research/`](ground/research/academic-research/) | ✅ |
| News Aggregation Agent | [`ground/research/news-aggregation/`](ground/research/news-aggregation/) | ✅ |
| Data Scout Agent | [`ground/research/data-scout/`](ground/research/data-scout/) | ✅ |

### Perimeter
| Agent | Folder | Prompt |
|-------|--------|--------|
| Entrance Bodyguard Agent | [`ground/perimeter/entrance-bodyguard/`](ground/perimeter/entrance-bodyguard/) | ✅ |

### Sentiment (7) — Ground
| Agent | Folder | Prompt |
|-------|--------|--------|
| Cathie Wood — Lead | [`ground/sentiment/cathie-wood/`](ground/sentiment/cathie-wood/) | ✅ |
| Jon Najarian — Options Flow & Dark Pool | [`ground/sentiment/options-flow-dark-pool/`](ground/sentiment/options-flow-dark-pool/) | ✅ |
| News Sentiment Agent | [`ground/sentiment/news-sentiment/`](ground/sentiment/news-sentiment/) | ✅ |
| Social Media & Retail Agent | [`ground/sentiment/social-media-retail/`](ground/sentiment/social-media-retail/) | ✅ |
| Insider & Institutional Agent | [`ground/sentiment/insider-institutional/`](ground/sentiment/insider-institutional/) | ✅ |
| Analyst & Earnings Revision Agent | [`ground/sentiment/analyst-earnings-revision/`](ground/sentiment/analyst-earnings-revision/) | ✅ |

### Alternative Data (13) — Ground
| Agent | Folder | Prompt |
|-------|--------|--------|
| Matthew Granade — Lead | [`ground/alt-data/matthew-granade/`](ground/alt-data/matthew-granade/) | ✅ |
| James Crawford — Satellite & Geospatial | [`ground/alt-data/satellite-geospatial/`](ground/alt-data/satellite-geospatial/) | ✅ |
| Supply Chain Agent | [`ground/alt-data/supply-chain/`](ground/alt-data/supply-chain/) | ✅ |
| Consumer Spending Agent | [`ground/alt-data/consumer-spending/`](ground/alt-data/consumer-spending/) | ✅ |
| Weather & Commodity Agent | [`ground/alt-data/weather-commodity/`](ground/alt-data/weather-commodity/) | ✅ |
| Web & App Traffic Agent | [`ground/alt-data/web-app-traffic/`](ground/alt-data/web-app-traffic/) | ✅ |

### Storage
| Agent | Folder | Prompt |
|-------|--------|--------|
| Storage Agent | [`ground/storage/storage/`](ground/storage/storage/) | ✅ |

### Macro (3) — Floor 2
| Agent | Folder | Prompt |
|-------|--------|--------|
| Larry Fink — Lead | [`floor-2/macro/larry-fink/`](floor-2/macro/larry-fink/) | ✅ |
| Ian Bremmer — Geopolitical Risk | [`floor-2/macro/geopolitical-risk/`](floor-2/macro/geopolitical-risk/) | ✅ |
| Central Bank & Liquidity Agent | [`floor-2/macro/central-bank-liquidity/`](floor-2/macro/central-bank-liquidity/) | ✅ |
| Currency & Sovereign Debt Agent | [`floor-2/macro/currency-sovereign-debt/`](floor-2/macro/currency-sovereign-debt/) | ✅ |
| Global Growth Tracker Agent | [`floor-2/macro/global-growth-tracker/`](floor-2/macro/global-growth-tracker/) | ✅ |

### Quant (4) — Floor 2
| Agent | Folder | Prompt |
|-------|--------|--------|
| Jim Simons — Lead | [`floor-2/quant/jim-simons/`](floor-2/quant/jim-simons/) | ✅ |
| Ed Thorp — Statistical Arbitrage | [`floor-2/quant/statistical-arbitrage/`](floor-2/quant/statistical-arbitrage/) | ✅ |
| Factor Analysis Agent | [`floor-2/quant/factor-analysis/`](floor-2/quant/factor-analysis/) | ✅ |
| Options & Volatility Agent | [`floor-2/quant/options-volatility/`](floor-2/quant/options-volatility/) | ✅ |
| Momentum & Trend Agent | [`floor-2/quant/momentum-trend/`](floor-2/quant/momentum-trend/) | ✅ |
| Machine Learning Agent | [`floor-2/quant/machine-learning/`](floor-2/quant/machine-learning/) | ✅ |
| Regime Detection Agent | [`floor-2/quant/regime-detection/`](floor-2/quant/regime-detection/) | ✅ |
| Risk Budgeting & Allocation Agent | [`floor-2/quant/risk-budgeting-allocation/`](floor-2/quant/risk-budgeting-allocation/) | ✅ |

### Fundamental (5) — Floor 2
| Agent | Folder | Prompt |
|-------|--------|--------|
| Warren Buffett — Lead | [`floor-2/fundamental/warren-buffett/`](floor-2/fundamental/warren-buffett/) | ✅ |
| Harry Markopolos — Forensic Accounting | [`floor-2/fundamental/forensic-accounting/`](floor-2/fundamental/forensic-accounting/) | ✅ |
| DCF & Valuation Agent | [`floor-2/fundamental/dcf-valuation/`](floor-2/fundamental/dcf-valuation/) | ✅ |
| Moat & Competitive Analysis Agent | [`floor-2/fundamental/moat-competitive-analysis/`](floor-2/fundamental/moat-competitive-analysis/) | ✅ |
| Management Quality Agent | [`floor-2/fundamental/management-quality/`](floor-2/fundamental/management-quality/) | ✅ |
| Catalyst & Event Agent | [`floor-2/fundamental/catalyst-event/`](floor-2/fundamental/catalyst-event/) | ✅ |
| Industry Structure Agent | [`floor-2/fundamental/industry-structure/`](floor-2/fundamental/industry-structure/) | ✅ |

### Technical (6) — Floor 2
| Agent | Folder | Prompt |
|-------|--------|--------|
| Mark Minervini — Lead | [`floor-2/technical/mark-minervini/`](floor-2/technical/mark-minervini/) | ✅ |
| Chart & Pattern Agent | [`floor-2/technical/chart-pattern/`](floor-2/technical/chart-pattern/) | ✅ |
| Volume & Order Flow Agent | [`floor-2/technical/volume-order-flow/`](floor-2/technical/volume-order-flow/) | ✅ |
| Market Microstructure Agent | [`floor-2/technical/market-microstructure/`](floor-2/technical/market-microstructure/) | ✅ |
| Technical Signal Engine Agent | [`floor-2/technical/technical-signal-engine/`](floor-2/technical/technical-signal-engine/) | ✅ |

### Crypto/Digital Assets (14) — Floor 2
| Agent | Folder | Prompt |
|-------|--------|--------|
| Vitalik Buterin — Lead | [`floor-2/crypto/vitalik-buterin/`](floor-2/crypto/vitalik-buterin/) | ✅ |
| Alex Svanevik — On-Chain Analytics | [`floor-2/crypto/on-chain-analytics/`](floor-2/crypto/on-chain-analytics/) | ✅ |
| DeFi & Yield Agent | [`floor-2/crypto/defi-yield/`](floor-2/crypto/defi-yield/) | ✅ |
| Tokenomics Agent | [`floor-2/crypto/tokenomics/`](floor-2/crypto/tokenomics/) | ✅ |
| Protocol Risk Agent | [`floor-2/crypto/protocol-risk/`](floor-2/crypto/protocol-risk/) | ✅ |

### Risk (2) — Floor 3
| Agent | Folder | Prompt |
|-------|--------|--------|
| Nassim Taleb — Lead | [`floor-3/risk/nassim-taleb/`](floor-3/risk/nassim-taleb/) | ✅ |
| Didier Sornette — Black Swan Detection | [`floor-3/risk/black-swan-detection/`](floor-3/risk/black-swan-detection/) | ✅ |
| VaR & Stress Test Agent | [`floor-3/risk/var-stress-test/`](floor-3/risk/var-stress-test/) | ✅ |
| Correlation & Concentration Agent | [`floor-3/risk/correlation-concentration/`](floor-3/risk/correlation-concentration/) | ✅ |
| Drawdown Monitor Agent | [`floor-3/risk/drawdown-monitor/`](floor-3/risk/drawdown-monitor/) | ✅ |
| Liquidity Risk Agent | [`floor-3/risk/liquidity-risk/`](floor-3/risk/liquidity-risk/) | ✅ |
| Factor Risk Agent | [`floor-3/risk/factor-risk/`](floor-3/risk/factor-risk/) | ✅ |

### Critique (11) — Floor 3
| Agent | Folder | Prompt |
|-------|--------|--------|
| Charlie Munger — Lead | [`floor-3/critique/charlie-munger/`](floor-3/critique/charlie-munger/) | ✅ |
| Meredith Whitney — Devil's Advocate | [`floor-3/critique/devils-advocate/`](floor-3/critique/devils-advocate/) | ✅ |
| Bear Case Intern | [`floor-3/critique/bear-case-intern/`](floor-3/critique/bear-case-intern/) | ✅ |
| Blind Spot Detector Agent | [`floor-3/critique/blind-spot-detector/`](floor-3/critique/blind-spot-detector/) | ✅ |
| Historical Analog Intern | [`floor-3/critique/historical-analog-intern/`](floor-3/critique/historical-analog-intern/) | ✅ |
| Assumption Challenger Agent | [`floor-3/critique/assumption-challenger/`](floor-3/critique/assumption-challenger/) | ✅ |
| Conflict Resolution Agent | [`floor-3/critique/conflict-resolution/`](floor-3/critique/conflict-resolution/) | ✅ |

### Compliance & Tax (12) — Floor 3
| Agent | Folder | Prompt |
|-------|--------|--------|
| Preet Bharara — Lead | [`floor-3/compliance/preet-bharara/`](floor-3/compliance/preet-bharara/) | ✅ |
| H. David Rosenbloom — Cross-Border Tax | [`floor-3/compliance/cross-border-tax/`](floor-3/compliance/cross-border-tax/) | ✅ |
| Regulatory Compliance Agent | [`floor-3/compliance/regulatory-compliance/`](floor-3/compliance/regulatory-compliance/) | ✅ |
| Trading Restriction Agent | [`floor-3/compliance/trading-restriction/`](floor-3/compliance/trading-restriction/) | ✅ |

### Strategy (8) — Floor 4
| Agent | Folder | Prompt |
|-------|--------|--------|
| David Swensen — Asset Allocation | [`floor-4/strategy/asset-allocation/`](floor-4/strategy/asset-allocation/) | ✅ |
| Tactical Overlay Intern | [`floor-4/strategy/tactical-overlay-intern/`](floor-4/strategy/tactical-overlay-intern/) | ✅ |
| Hedging & Protection Agent | [`floor-4/strategy/hedging-protection/`](floor-4/strategy/hedging-protection/) | ✅ |
| Tax Optimization Agent | [`floor-4/strategy/tax-optimization/`](floor-4/strategy/tax-optimization/) | ✅ |
| Portfolio Construction Agent | [`floor-4/strategy/portfolio-construction/`](floor-4/strategy/portfolio-construction/) | ✅ |
| Position Sizing Intern | [`floor-4/strategy/position-sizing-intern/`](floor-4/strategy/position-sizing-intern/) | ✅ |

### Execution (9) — Floor 4
| Agent | Folder | Prompt |
|-------|--------|--------|
| Order Routing Agent | [`floor-4/execution/order-routing/`](floor-4/execution/order-routing/) | ✅ |
| Execution Algorithm Agent | [`floor-4/execution/execution-algorithm/`](floor-4/execution/execution-algorithm/) | ✅ |
| Timing & Slippage Agent | [`floor-4/execution/timing-slippage/`](floor-4/execution/timing-slippage/) | ✅ |
| Pre-Flight Check Agent | [`floor-4/execution/pre-flight-check/`](floor-4/execution/pre-flight-check/) | ✅ |

### Memory (10) — Floor 4
| Agent | Folder | Prompt |
|-------|--------|--------|
| Knowledge Graph Agent | [`floor-4/memory/knowledge-graph/`](floor-4/memory/knowledge-graph/) | ✅ |
| Learning & Reflection Agent | [`floor-4/memory/learning-reflection/`](floor-4/memory/learning-reflection/) | ✅ |

### Control (15) — Floor 4
| Agent | Folder | Prompt |
|-------|--------|--------|
| Quality Control Agent | [`floor-4/control/quality-control/`](floor-4/control/quality-control/) | ✅ |
| Agent Health Monitor | [`floor-4/control/agent-health-monitor/`](floor-4/control/agent-health-monitor/) | ✅ |

### Tasks (16) — Floor 4
| Agent | Folder | Prompt |
|-------|--------|--------|
| Daily Briefing Agent | [`floor-4/tasks/daily-briefing/`](floor-4/tasks/daily-briefing/) | ✅ |
| Opportunity Scout Agent | [`floor-4/tasks/opportunity-scout/`](floor-4/tasks/opportunity-scout/) | ✅ |

### Penthouse (orchestrator-era)
| Agent | Folder | Prompt |
|-------|--------|--------|
| Portfolio Manager | [`penthouse/agents/portfolio-manager/`](penthouse/agents/portfolio-manager/) | ✅ |
| PM Bodyguard | [`penthouse/agents/pm-bodyguard/`](penthouse/agents/pm-bodyguard/) | ✅ |

## Prompt Engineering Framework

| Doc | Purpose |
|-----|---------|
| [`SYSTEM-PROMPT-FRAMEWORK.md`](SYSTEM-PROMPT-FRAMEWORK.md) | Baseline prompt structure (protocols, gates, formats) |
| [`SYSTEM-PROMPT-AUDIT-FRAMEWORK.md`](SYSTEM-PROMPT-AUDIT-FRAMEWORK.md) | Audit checklist for prompt compliance |
| [`SYSTEM-PROMPT-IMPROVEMENTS-*.md`](SYSTEM-PROMPT-IMPROVEMENTS-SUMMARY.md) | Applied improvements log |
| [`SYSTEM-PROMPT-IMPROVEMENT-TEMPLATES.md`](SYSTEM-PROMPT-IMPROVEMENT-TEMPLATES.md) | T2/T3/T4 improvement templates |
| [`LEAD-PROMPT-TEST-TEMPLATE.md`](LEAD-PROMPT-TEST-TEMPLATE.md) | T1 lead test template |
| [`T2-NAMED-AGENT-TEST-TEMPLATE.md`](T2-NAMED-AGENT-TEST-TEMPLATE.md) / [`T3-UTILITY-AGENT-TEST-TEMPLATE.md`](T3-UTILITY-AGENT-TEST-TEMPLATE.md) / [`T4-INTERN-TEST-TEMPLATE.md`](T4-INTERN-TEST-TEMPLATE.md) | Tier test templates |
| [`scripts/validate-system-prompts.py`](scripts/validate-system-prompts.py) | Validates all 89 prompts (tier protocols, per-asset gates, freshness, FROM/TO format) |
