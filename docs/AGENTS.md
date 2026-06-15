AGENTS.md
The Complete Agent System for Labourious
This document defines every agent type available in Labourious, what they do, how they work, and how to customize them.

TABLE OF CONTENTS

Agent System Overview
Agent Taxonomy (Full List)
Day Trading Room Agents
Sector Trading Room Agents
Long-Term Investment Room Agents
Meta Agents (Control & Monitoring)
Prebuilt Agents (Ready-to-Deploy)
Context File Reference
Confidence Score System
Agent Customization Guide
Conflict Resolution
Example Agent Deployments


Agent System Overview
What is an Agent?
An agent is an autonomous AI entity that trades according to a set of rules you define. Every agent:

Reads live market data
Consults a context file (your trading rules)
Asks the LLM: "Should we trade based on these rules and this data?"
Executes or waits for approval (depending on mode)
Logs results and updates confidence score

Agent Lifecycle
Agent Created
    ↓
Paper Trading (3 days mandatory minimum)
    ↓
Confidence Score 50%+ reached
    ↓
User approves switch to live trading
    ↓
Agent executes real trades
    ↓
Risk Management monitors performance
    ↓
Auto-pause if losing streak detected
    ↓
User reviews diagnosis, fixes context/APIs
    ↓
Resume with reset confidence score
Key Characteristics of Agents
PropertyMeaningRoomDay Trading, Sector Trading, Long-Term Investment, or MetaTimeframeMinutes (day traders) to months (investors)Entry SignalWhat triggers a trade (news, sector strength, valuation)Exit SignalWhen to close a positionContext FileYour custom rules; agent reads this to decideConfidence ScoreHow trustworthy the agent is (10-100%)Execution ModeAutonomous, Human-in-Loop, or Risk-BasedData SourcesAPIs the agent reads (free or paid)Position SizeHow much capital agent can use per tradeFrequencyHow often agent checks data (every 5 min to weekly)

Agent Taxonomy (Full List)
Visual Overview
┌──────────────────────────────────────────────────────────────────┐
│                   LABOURIOUS AGENT ECOSYSTEM                      │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              DAY TRADING ROOM                           │    │
│  │  (Fast, News/Signals/Prediction Driven, Minutes-Hours) │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ✓ News Agent           (Prebuilt)                      │    │
│  │ ✓ Technical Signals    (Prebuilt)                      │    │
│  │ ✓ Prediction Markets   (Prebuilt)                      │    │
│  │ + More prebuilt agents available                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │          SECTOR TRADING ROOM                            │    │
│  │  (Medium, Sector-Focused, Days to Weeks)               │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ • Energy Sector Trader                                  │    │
│  │ • Technology Sector Trader                              │    │
│  │ • Healthcare Sector Trader                              │    │
│  │ • Finance Sector Trader                                 │    │
│  │ • Materials Sector Trader                               │    │
│  │ • Consumer Sector Trader                                │    │
│  │ • Utilities Sector Trader                               │    │
│  │ + Custom sector traders (user-created)                  │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │       LONG-TERM INVESTMENT ROOM                         │    │
│  │  (Slow, Fundamental, Months to Years)                  │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ✓ Stock Picker Agent    (Prebuilt)                     │    │
│  │ ✓ Index Agent           (Prebuilt)                     │    │
│  │ + More prebuilt strategies available                    │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │         META AGENTS (Control Room)                      │    │
│  │  (Monitoring, Summarization, Execution Control)        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │ ✓ Risk Management Agent  (Always Active)               │    │
│  │ ✓ Bodyguard Agent        (Always Active)               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘

Day Trading Room Agents
Overview
Day trading agents operate on minutes to hours. They react to:

Real-time news and announcements
Technical signals
Prediction market opportunities

These agents are aggressive and fast. They require either:

Very short approval windows (2-5 seconds)
Pre-authorized autonomous execution
High confidence thresholds

Default Execution Mode: Human-in-Loop or Autonomous (user's choice)
Default Approval Timeout: 5-30 seconds

AGENT #1: NEWS AGENT (Prebuilt)
Purpose: Catch immediate market reactions to breaking news and announcements.
What It Does:

Monitors 1-3 real-time news APIs (default: Finnhub free tier + Twitter/X API + optional paid Bloomberg)
Detects market-moving announcements (FDA approvals, earnings, macro events, company news)
Reads your context file to determine if the news is bullish or bearish
Enters trade immediately if context rules match
Exits when market stabilizes and initial reaction is priced in

Data Sources (v1.0):

Finnhub News API (free, 50 requests/day)
Twitter/X API (real-time company mentions, optional)
Custom news sources (user can add RSS feeds, not recommended for accuracy)
Optional paid: Bloomberg API, Facteus

Entry Logic:
TRIGGER: Breaking news detected
    ↓
CONTEXT ANALYSIS: "Is this news bullish or bearish for this asset?"
    ↓
CONFIDENCE CHECK: Is LLM confidence > 60%?
    ↓
    YES → Execute trade
    NO  → Skip (wait for next signal)
    ↓
ENTRY: Place market order, size = context file setting
Exit Logic (Recommended Strategy):
The most successful news traders exit quickly after capturing the immediate move. Here's the recommended approach:
EXIT TRIGGERS (whichever comes first):

1. MOMENTUM REVERSAL
   └─ Use RSI or MACD to detect when momentum weakens
   └─ Example: Entry after +2% spike, exit when momentum goes negative
   └─ Captures 50-70% of full expected move

2. TIME-BASED CAP
   └─ Maximum hold: 30 minutes
   └─ News impact usually fades in 15-60 minutes
   └─ After 30 min, exit regardless of P&L

3. VOLATILITY DROP
   └─ When volatility (ATR) drops 50% from spike
   └─ Signals: "News reaction complete, time to exit"

4. PROFIT TARGET
   └─ Take 70% of expected move (don't wait for 100%)
   └─ Prioritize consistency over home runs
   └─ Example: Stock should move 5% on this news
             Exit when up 3-4%, keep some off table

EXAMPLE:
- FDA approves Pharma drug
- Stock jumps 3% in first minute
- Agent buys at +1.5%
- Stock continues to +3.5% over 10 minutes
- Agent's momentum indicator shows reversal
- EXIT: Take profit at +2.8% (captured 80% of move)
- Time in trade: 8 minutes
- Win: Captured quick profit, avoided reversal
Context File Example:
AGENT: News Trader - Biotech
ASSET: Biotech stocks (BIOPSY, CRSP, etc.)
DATA SOURCES: Finnhub + Bloomberg

WHAT MAKES NEWS TRADEABLE?
- FDA drug approval/rejection (bullish/bearish)
- Clinical trial results (efficacy data)
- Patent news (positive = bullish)
- SEC filings indicating fraud (bearish)
- AVOID: Analyst upgrades/downgrades (not actual news)

ENTRY RULES:
1. Major FDA news detected
2. News is from official source (not rumor)
3. Drug affects > $1B market segment
4. Company fundamentals are not broken (not shorting into bankruptcy)

POSITION SIZING:
- Small biotech (< $5B market cap): 0.5% account size
- Mid biotech ($5-20B): 1% account size
- Large biotech (> $20B): 1-2% account size

EXIT RULES:
- Exit if momentum reverses (RSI > 70 then < 60)
- Exit if 30 minutes have passed
- Exit if profit target reached (70% of expected move)
- Do NOT hold through market close (news risk still high)

BLACKOUT PERIODS:
- Skip trading during Fed announcements
- Skip during major macro events (jobs report, GDP)
- Skip 15 minutes after market open (high volatility first 30 min)

CONFIDENCE FACTORS:
- Base: 10% (just context file)
- +15% if Finnhub connected (trusted source)
- +20% if Bloomberg API connected (professional data)
- +10% per 10 successful trades (earned confidence)
Configuration (User Settings):
json{
  "agent_name": "Biotech News Trader",
  "enabled": true,
  "room": "day_trading",
  "asset_class": "stocks",
  "sectors": ["healthcare", "biotech"],
  "context_file": "contexts/biotech_news.txt",
  
  "data_sources": {
    "primary": "finnhub",
    "secondary": "twitter_api",
    "tertiary": "custom_rss"
  },
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 10,
    "auto_approve_if_confidence_above": 85
  },
  
  "trading": {
    "position_size_percent": 1.0,
    "max_concurrent_positions": 3,
    "stop_loss_percent": -3.0,
    "take_profit_percent": 2.5,
    "max_hold_minutes": 30
  },
  
  "timing": {
    "check_frequency": "realtime",
    "trading_hours": "09:30-16:00 EST",
    "skip_first_30_minutes": true,
    "skip_market_close": true
  },
  
  "paper_trading": {
    "enabled": true,
    "duration_days": 3,
    "initial_balance": 100000
  }
}
Confidence Scoring:
Starting Confidence: 10%

Increases:
+ 5% for each data source connected (Finnhub, Bloomberg, Twitter)
+ 10% per 10 consecutive winning trades
+ 5% if context file is detailed and specific

Decreases:
- 10% for each losing trade
- 20% if auto-paused for under-performance
- Can drop to 0% if losing streak > 5 trades

Threshold to go live:
- Minimum: 50% (not recommended)
- Recommended: 70%+
- Very safe: 85%+
Prebuilt Templates:

Biotech News Trader
Earnings Surprise Trader
FDA/Regulatory News Trader
Macro Economic News Trader (Fed, jobs, GDP)


AGENT #2: TECHNICAL SIGNALS AGENT (Prebuilt)
Purpose: Trade based on technical analysis signals (RSI, MACD, moving averages, chart patterns).
What It Does:

Monitors price, volume, and technical indicators
Detects signals: overbought/oversold, moving average crosses, momentum breaks
Reads context file to determine which signals to trade
Enters when signal confirms
Exits when opposite signal triggers

Data Sources (v1.0):

Alpha Vantage (free: 5 calls/min, 500/day)
IEX Cloud (free tier available)
Broker's market data (included with account)

Entry Logic:
TRIGGER: Technical indicator signal detected
    ↓
CONTEXT CHECK: "Should we trade this signal?"
    ↓
CONFIRMATION: Is secondary indicator also positive?
    ↓
    YES → Enter position
    NO  → Wait for confirmation
Exit Logic:
EXIT when:
1. Opposite signal triggers (RSI was < 30, now > 70)
2. Breakout fails (price returns below entry)
3. Stop loss hit
4. Profit target reached
5. Volume dries up (thin market warning)
Context File Example:
AGENT: Technical Signals Trader
ASSETS: High-beta tech stocks (NVDA, TSLA, AMD, etc.)

PRIMARY SIGNALS:
1. RSI(14) < 30 (oversold) + RSI starts rising = BUY
2. MACD crosses above signal line = BUY
3. Price breaks above 50-day MA on high volume = BUY

EXIT SIGNALS:
1. RSI > 70 (overbought) = SELL
2. MACD crosses below signal line = SELL
3. Price closes below 50-day MA = SELL
4. Volume dries up (< 50% average) = SELL
5. Stop loss: -5% below entry
6. Take profit: +10% above entry

POSITION SIZING:
- Conservative: 0.5% per signal
- Moderate: 1% per signal
- Max concurrent positions: 5

TIMEFRAME:
- Entry: Day of signal
- Hold: 2-10 days (not a day trader, but faster than swing)
- Exit: When signal reverses or target hit

AVOID:
- Trading during market open (first 30 minutes, high noise)
- Trading illiquid stocks (volume < 1M shares/day)
- Averaging down (never add to losing position)

AGENT #3: PREDICTION MARKET AGENT (Prebuilt)
Purpose: Trade on Kalshi and Polymarket prediction markets based on research and analysis.
What It Does:

Monitors upcoming prediction market events (elections, sports, economics, etc.)
Analyzes news, historical data, and smart money positioning
Compares Kalshi vs Polymarket odds to find mispricings
Enters position on the market with better risk/reward
Exits when prediction resolves

Data Sources (v1.0):

Kalshi API (direct market access)
Polymarket API (direct market access)
News APIs (context for predictions)
Sports data APIs (for sports predictions)
Historical odds data (for calibration)

Entry Logic:
TRIGGER: Upcoming prediction market event
    ↓
RESEARCH: Analyze all available information
    - Recent news
    - Historical patterns
    - Expert opinions
    - Crowd wisdom (check odds movements)
    ↓
CONTEXT ANALYSIS: "What's my edge here?"
    ↓
CONFIDENCE CHECK: Is LLM confidence >= 75%?
    ↓
    YES → Find best market (Kalshi vs Polymarket)
    NO  → Skip event
    ↓
MARKET SELECTION: Which gives better odds?
    ↓
ENTRY: Bet size based on confidence
Exit Logic:
EXIT when:
1. Prediction resolves (market closes)
2. Mid-trade consensus changes significantly
   └─ Example: New polling shows dramatic shift
   └─ Close position early to reduce loss
3. Risk limit hit (-$X max loss per bet)
Context File Example:
AGENT: Prediction Market Trader
MARKETS: Kalshi + Polymarket

PREDICTION TYPES I TRADE:
1. Sports (NFL, NBA, MLB, college sports)
   └─ Data source: ESPN API, advanced stats
   └─ Edge: Understand team dynamics, injury reports, coaching changes
   
2. Elections & Politics
   └─ Data source: Polling aggregators, news
   └─ Edge: Early polling trends before crowd catches on
   
3. Economic Events (Inflation, Jobs, GDP)
   └─ Data source: Economic calendars, forecasts
   └─ Edge: Understand surprises vs expectations
   
4. Tech/Business Events (IPO, acquisitions, regulations)
   └─ Data source: SEC filings, news, insider trading
   └─ Edge: Understand regulatory landscape

ENTRY RULES:
1. Confidence in prediction >= 75%
2. Odds provide favorable risk/reward (at least 2:1)
3. Market liquidity is sufficient (can exit if needed)
4. Not a consensus event (crowd already priced it in)

POSITION SIZING:
- Very high confidence (>85%): $500-1000 per bet
- High confidence (75-85%): $200-500 per bet
- Medium confidence (60-75%): $50-200 per bet
- Low confidence (<60%): Skip the bet

MARKET SELECTION:
- If Kalshi odds: 55% vs Polymarket odds: 52% for same outcome
- → Bet on Polymarket (better odds)
- Always choose the market with better odds

EXIT RULES:
- Hold until prediction resolves (natural exit)
- Exit early if consensus dramatically changes
- Max loss per bet: -$100 (then reassess)

BLACKOUT:
- Don't trade late-night events (emotion + fatigue)
- Don't trade events 10 minutes before market close
- Don't trade during major news events (conflicts)
Configuration (User Settings):
json{
  "agent_name": "Prediction Market Trader",
  "enabled": true,
  "room": "day_trading",
  "context_file": "contexts/prediction_markets.txt",
  
  "markets": {
    "kalshi": { "api_key": "[user_provides]", "enabled": true },
    "polymarket": { "api_key": "[user_provides]", "enabled": true }
  },
  
  "data_sources": {
    "sports": "espn_api",
    "elections": "polling_aggregator",
    "economics": "fred_api",
    "news": "finnhub"
  },
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 30
  },
  
  "betting": {
    "bet_sizing_strategy": "kelly_criterion",
    "min_confidence_to_trade": 75,
    "max_bet_per_market": 1000,
    "max_total_exposure": 5000,
    "max_loss_per_bet": 100
  },
  
  "timing": {
    "check_frequency": "daily",
    "look_ahead_days": 30,
    "skip_late_night": true
  }
}

OTHER PREBUILT DAY TRADING AGENTS
Users can choose from additional prebuilt agents in v1.0:

Earnings Surprise Trader (trades stocks after earnings beats/misses)
Macro Economic Trader (Fed decisions, jobs reports, GDP)
Crypto News Trader (Bitcoin, Ethereum, major coins)
Volatility Spike Trader (VIX spikes = trading opportunity)
Gap Trader (stocks that gapped up/down at open)
[More can be added as templates]


Sector Trading Room Agents
Overview
Sector trading agents operate on days to weeks. They trade within a sector based on:

Relative sector strength
Sector-specific news and events
Technical setup within the sector
Macro conditions affecting that sector

These agents are medium-frequency traders. They hold positions long enough to capture a trend, but exit if the sector thesis breaks.
Default Execution Mode: Human-in-Loop (30 second approval window)
Default Frequency: Daily data checks

AGENT TEMPLATE: SECTOR TRADER
7 Pre-built Sector Traders (One per Major S&P Sector):

Energy Sector Trader (XLE)
Technology Sector Trader (XLK)
Healthcare Sector Trader (XLV)
Finance Sector Trader (XLF)
Materials Sector Trader (XLB)
Consumer Sector Trader (XLY/XLP)
Utilities Sector Trader (XLU)


ENERGY SECTOR TRADER (Example)
Purpose: Capture sector rotation into/out of Energy based on macro conditions and sector momentum.
What It Does:

Monitors energy sector relative strength vs S&P 500
Tracks oil prices, geopolitical events, and macro factors
Identifies best energy stocks to own when sector is strong
Enters position when sector setup is positive
Holds for days-weeks until sector thesis breaks
Exits completely if sector future looks bad

Data Sources (v1.0):

Sector price data (broker API)
Oil futures data (Alpha Vantage, Finnhub)
Geopolitical news (Reuters, Bloomberg)
Macro calendar (economic indicators)
Options flow (unusual activity in sector)

Entry Logic:
TRIGGER: Energy sector shows relative strength
    ↓
CHECK 1: XLE outperforming S&P 500 by 2%+ (5-day)
    ↓
CHECK 2: Oil prices above 20-day MA
    ↓
CHECK 3: No major geopolitical crisis (news sentiment positive)
    ↓
CHECK 4: Macro data supports (inflation, Fed policy)
    ↓
    ALL CHECKS PASS → Identify best energy stocks to buy
    ↓
ENTRY: Buy XLE or individual energy stocks
        Position size: 5-10% of account
        Sector allocation: 50-100% of available capital
Exit Logic:
FULL EXIT when:
1. Sector momentum breaks
   └─ XLE underperforms S&P 500 for 3+ consecutive days
   └─ Oil prices close below 20-day MA
   
2. Macro conditions worsen
   └─ Fed raises rates unexpectedly
   └─ Economic recession signals
   └─ Geopolitical crisis emerges
   
3. Time-based (quarterly rebalance)
   └─ Even if thesis still valid, rotate capital
   
4. Profit target reached
   └─ Take +15-20% profit, redeploy elsewhere
   
HOLDING PERIOD:
- Minimum: 3-5 days
- Target: 1-4 weeks
- Maximum: 8-12 weeks (then reassess)

EXAMPLE EXIT:
- Entered energy position: Oil $75/barrel, XLE at $85
- Held for 2 weeks, Oil up to $82, XLE at $94 (+10%)
- Fed signals rate hikes incoming (bad for energy demand)
- Context analysis: "Rate hikes will slow economy, reduce energy demand"
- DECISION: Exit entire position, redeploy to defensive sectors
- TIME IN POSITION: 12 days
- RESULT: +10% gain, avoided the reversal
Context File Example:
AGENT: Energy Sector Trader
SECTOR: Energy (XLE)
HOLDING PERIOD: 3-21 days (data-driven, market-driven)

ENTRY CONDITIONS (ALL must be true):
1. XLE outperforming S&P 500 by 2%+ over last 5 days
   └─ Measured as: (XLE 5-day return) > (SPY 5-day return) + 2%
   
2. Oil prices (WTI crude) above 20-day moving average
   └─ Confirms uptrend, not just bounce
   
3. Macro conditions supportive
   └─ Fed not aggressively tightening
   └─ No imminent recession signals
   └─ Inflation not spiking (bad for demand)
   
4. No major geopolitical crisis
   └─ No OPEC disruptions
   └─ No unexpected supply shocks

BEST STOCKS TO BUY WHEN ENTERING:
- XLE (Sector ETF - most liquid)
- OR individual oil companies:
  └─ Large cap: XOM, CVX (dividend stable)
  └─ Mid cap: MPC, PSX (refiner exposure)
  └─ Small cap: If sector hot, more upside

POSITION SIZING:
- Start: 5% of account in sector
- Scale up to: 10% if momentum accelerates
- Max: 15% (don't over-concentrate)

EXIT CONDITIONS (ANY trigger full exit):
1. Sector Momentum Breaks
   └─ XLE underperforms SPY for 3 consecutive days
   └─ OR oil closes below 20-day MA on high volume
   
2. Macro Deterioration
   └─ Fed announces surprise rate hike
   └─ Recession probability rises above 30%
   └─ GDP forecast revised downward
   └─ Unemployment rises unexpectedly
   
3. Geopolitical Event
   └─ Major supply disruption (pipeline, refinery incident)
   └─ Political instability (coup, war)
   └─ → Exit immediately (don't wait for confirmation)
   
4. Take Profit Target
   └─ When up 15-20%, consider taking full position
   └─ Can hold for more, but secure some gains
   
5. Time Limit
   └─ After 3-4 weeks, reassess thesis
   └─ Don't let positions become "dead money"

STOP LOSS:
- Hard stop: -8% from entry
- If position down 8%, exit and review thesis

WEEKLY REBALANCE:
- Every Friday EOD, review:
  └─ Is sector thesis still valid?
  └─ Should we increase/decrease allocation?
  └─ Any new macro catalysts?

DATA TO MONITOR DAILY:
- Oil prices (WTI, Brent)
- XLE price and volume
- USD strength (strong USD = worse for oil)
- Sector options flow (smart money positioning)
- Macro calendar (Fed speakers, economic data)
- News (supply, demand, geopolitical)
Configuration (User Settings):
json{
  "agent_name": "Energy Sector Trader",
  "enabled": true,
  "room": "sector_trading",
  "sector": "energy",
  "etf": "XLE",
  "context_file": "contexts/energy_sector_trader.txt",
  
  "data_sources": {
    "sector_prices": "broker_api",
    "oil_prices": "alpha_vantage",
    "macro_data": "fred_api",
    "news": "finnhub",
    "options_flow": "optional_paid_api"
  },
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 30
  },
  
  "trading": {
    "position_size_percent": 5.0,
    "max_allocation": 15.0,
    "stop_loss_percent": -8.0,
    "take_profit_percent": 15.0,
    "min_hold_days": 3,
    "max_hold_days": 21
  },
  
  "timing": {
    "check_frequency": "daily",
    "trading_hours": "09:30-16:00 EST",
    "rebalance_frequency": "weekly"
  },
  
  "alerts": {
    "notify_on_entry": true,
    "notify_on_exit": true,
    "notify_on_thesis_break": true
  }
}
Confidence Scoring for Sector Traders:
Starting: 10%

Increases:
+ 10% if options flow data connected (smart money positioning)
+ 10% if macro data (FRED API) connected
+ 5% for sector-specific news API connected
+ 5% per 3 winning sectors (out of 7, diversification credit)
+ 5% if context file is detailed (shows deep sector knowledge)

Decreases:
- 5% for each losing trade
- 10% if sector thesis breaks but agent takes loss
- 15% if agent holds through obvious exit signal
- Can drop to 0% if wrong on sector 5+ consecutive times

Threshold to go live:
- Minimum: 50%
- Recommended: 70%
- Safe: 85%+

OTHER PREBUILT SECTOR TRADERS
All 7 sectors follow the same template:
SectorETFKey DriversEnergyXLEOil prices, geopolitical, energy demandTechnologyXLKGrowth rates, earnings, tech trends, Fed policyHealthcareXLVDrug approvals, healthcare spending, politicsFinanceXLFInterest rates, bank earnings, loan demandMaterialsXLBCommodity prices, economic growthConsumerXLY/XLPUnemployment, consumer spending, inflationUtilitiesXLUInterest rates, inflation, energy prices

Long-Term Investment Room Agents
Overview
Long-term investment agents operate on months to years. They:

Buy quality investments and hold
Make deliberate, researched decisions
Monitor quarterly and adjust
Use fundamental analysis and valuation

These agents are patient, thoughtful, and data-driven. They execute human-like investment strategy.
Default Execution Mode: Human-in-Loop (approval, but 5-minute windows)
Default Frequency: Weekly check-in, monthly review, quarterly rebalance

AGENT #1: STOCK PICKER AGENT
Purpose: Find undervalued individual stocks and build a concentrated portfolio.
What It Does:

Reads SEC filings (10-K, 10-Q, 8-K)
Analyzes fundamentals (earnings, cash flow, debt, growth)
Calculates intrinsic value (DCF model)
Checks valuation metrics (P/E, P/B, dividend yield)
Reviews hedge fund ownership (smart money buying?)
Runs 10 mini-agents (10 pros / 10 cons analysis)
Decides: Buy, Hold, or Sell
Executes or recommends
Monitors holdings weekly, reviews quarterly

Mini-Agents (Internal Reasoning):
The stock picker delegates detailed analysis to 10 "pro" mini-agents and 10 "con" mini-agents:
10 Pro Mini-Agents (These analyze positive factors):

Growth Analyst: "Is revenue/earnings growing?"
Profitability Analyst: "Is the company profitable and becoming more so?"
Valuation Analyst: "Is the stock cheap relative to earnings?"
Cash Flow Analyst: "Is free cash flow strong and improving?"
Dividend Analyst: "Does the company pay sustainable dividends?"
Balance Sheet Analyst: "Is debt manageable? Equity strong?"
Competitive Analyst: "Does the company have moat/competitive advantage?"
Insider Buying Analyst: "Are executives buying stock (good sign)?"
Institutional Ownership Analyst: "Are hedge funds/institutions buying?"
Sector Analyst: "Is this sector in favor? Tailwinds present?"

10 Con Mini-Agents (These analyze negative factors):

Debt Risk Analyst: "Is debt too high? Refinancing risk?"
Earnings Quality Analyst: "Are earnings real or accounting tricks?"
Valuation Stretched Analyst: "Is stock overvalued despite growth?"
Cash Burn Analyst: "Is company burning cash? Runway issues?"
Competition Analyst: "Are new competitors threatening market share?"
Regulatory Analyst: "Are there regulatory headwinds or litigation risks?"
Insider Selling Analyst: "Are executives/insiders selling? Bad sign?"
Guidance Miss Analyst: "Does company consistently miss guidance?"
Industry Headwinds Analyst: "Is sector/industry in decline?"
Red Flag Analyst: "Are there accounting red flags, fraud risks?"

How It Works:
User selects a stock to analyze: NVDA
    ↓
CONTEXT FILE REVIEW:
- What are our investment criteria?
- What metrics matter most?
- What valuation range do we want?
    ↓
DATA GATHERING:
- Fetch latest 10-K, 10-Q
- Fetch earnings history
- Calculate key metrics
- Get valuation data
    ↓
MINI-AGENT ANALYSIS:
- 10 Pro-agents each analyze 1 positive factor
- 10 Con-agents each analyze 1 negative factor
- All 20 produce summaries
    ↓
WEIGHTED SCORING:
- Weight pro-agents: Growth (3x), Profitability (2x), Valuation (2x), etc.
- Weight con-agents: Debt (3x), Valuation Stretched (2x), etc.
- Calculate total pro score vs con score
    ↓
LLM SYNTHESIS:
- "Pros: 73 points. Cons: 52 points."
- "Overall: NVDA is fairly valued but has strong growth."
- Recommendation: BUY if price < $X, HOLD if between $X-$Y, SELL if > $Y
    ↓
USER APPROVAL:
- Show user the analysis
- User approves or rejects
    ↓
EXECUTION:
- If BUY approved: Position size 3-5% per stock
- If HOLD approved: Monitor quarterly
- If SELL: Close position
    ↓
MONITORING:
- Weekly check: "Any major news changes thesis?"
- Monthly review: "How is position performing?"
- Quarterly rebalance: "Should I add, trim, or exit?"
Data Sources (v1.0):

SEC Edgar API (free, all filings)
Alpha Vantage (free tier: company fundamentals)
Yahoo Finance API (free, historical data)
Finnhub (free tier: news, ownership data)
Optional paid: FactSet, Refinitiv (deeper research)

Entry Logic:
STOCK IDENTIFIED (e.g., NVDA)
    ↓
CONTEXT FILE ANALYSIS:
"What do we look for in tech stocks?"
- Growth > 10% annually
- P/E < 25 (reasonable valuation)
- Debt/Equity < 1.5 (manageable debt)
- Insider buying in last 6 months
- Institutional ownership > 50%
    ↓
MINI-AGENT EXECUTION:
- All 20 mini-agents analyze the stock
- Each produces: Score (0-10) + Reasoning
    ↓
WEIGHTED CONSENSUS:
- Pro Score: 73/100 (Growth +10, Profitability +10, etc.)
- Con Score: 52/100 (Valuation at high end -8, Competition -6, etc.)
- Net: LEAN BUY (+21 points in favor)
    ↓
VALUATION DECISION:
- Intrinsic value: $450 per DCF model
- Current price: $420
- Margin of safety: 7%
- Decision: BUY (price below intrinsic value)
    ↓
ENTRY: Buy 3-5% of portfolio in NVDA
Exit Logic:
HOLD MONITORING:
- Every week: Check for major news/changes
- Every month: Review position P&L
- Every quarter: Full re-analysis

EXIT TRIGGER when:
1. VALUATION REACHED
   └─ Intrinsic value was $450, stock now $450
   └─ "Thesis is complete, take profit"
   └─ Exit: Sell full position
   
2. THESIS BREAKS
   └─ Major management change
   └─ Unexpected competitive threat
   └─ Earnings miss suggests business problem
   └─ Exit: Sell full position
   
3. BETTER OPPORTUNITY
   └─ Found better stock (higher return potential)
   └─ Exit: Trim or sell to redeploy
   
4. EMERGENCY EXIT
   └─ Market crash (portfolio down 20%+)
   └─ Company negative news (fraud, bankruptcy risk)
   └─ Exit: Sell to raise cash / reduce portfolio beta

POSITION MANAGEMENT:
- Once profitable, consider trimming 20-30% to lock in gains
- If stock doubles, take 50% profit, hold rest for upside
- Don't average down (never add to losing position)
- Set alerts for major news or analyst changes
Context File Example:
AGENT: Stock Picker - Value Investor
INVESTMENT STYLE: Value investing (find undervalued quality companies)

INVESTMENT CRITERIA:
Must have ALL of these:
1. Earnings growth > 5% annually (not just revenue)
2. P/E ratio < market average (reasonable valuation)
3. Debt/Equity < 1.5 (manageable debt)
4. Free cash flow positive and growing
5. Dividend yield > 1.5% OR reinvestable profits

SECTORS I LIKE:
- Healthcare (steady growth, aging population)
- Financials (reasonable valuations often)
- Consumer Staples (defensive, recurring revenue)

SECTORS TO AVOID:
- Pre-revenue biotech (too speculative)
- Money-losing startups (hope stocks)
- Heavily leveraged companies (bankruptcy risk)

VALUATION METRICS:
Target P/E: 12-18 (depending on growth rate)
Target P/B: 1.0-2.0
Target PEG: < 1.0 (price/earnings/growth)
Dividend Yield: > 2% preferred

RED FLAGS (Exit immediately):
- Accounting irregularities or restatements
- Insiders selling aggressively
- Major litigation or regulatory issues
- Missed guidance multiple quarters
- Declining competitive position

GREEN FLAGS (Buy more):
- Insider buying (management confident)
- Activist investor buying (smart money)
- New product launch with potential
- Analyst upgrades with solid reasoning
- Share buyback at low valuations

POSITION SIZING:
- New position: 3% of account
- Undervalued position: 5% of account
- Max per position: 7%
- Max sector: 25%
- Total stocks: 15-25 positions (diversified)

REBALANCE FREQUENCY:
- Weekly check: Any major news?
- Monthly review: How's it performing?
- Quarterly: Full re-analysis, add/trim/exit
- Yearly: Full portfolio review

HOLD PERIOD:
- Minimum: 6 months (be patient)
- Target: 1-3 years (let thesis play out)
- Maximum: 5+ years (if thesis still valid)
- Max loss: -25% then reassess thesis
Configuration:
json{
  "agent_name": "Stock Picker",
  "enabled": true,
  "room": "long_term_investment",
  "investment_style": "value_investing",
  "context_file": "contexts/stock_picker_value.txt",
  
  "data_sources": {
    "sec_filings": "edgar_api",
    "fundamentals": "alpha_vantage",
    "historical": "yahoo_finance",
    "news": "finnhub",
    "insider_trades": "optional_paid"
  },
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 300
  },
  
  "trading": {
    "position_size_percent": 3.0,
    "max_position_size": 7.0,
    "max_sector_exposure": 25.0,
    "max_positions": 25,
    "stop_loss_percent": -25.0,
    "take_profit_percent": 100.0
  },
  
  "mini_agents": {
    "enabled": true,
    "pro_agents": 10,
    "con_agents": 10,
    "pro_weighting": {
      "growth": 3,
      "profitability": 2,
      "valuation": 2,
      "cash_flow": 2,
      "dividend": 1,
      "debt": 2,
      "competitive_advantage": 2,
      "insider_buying": 1,
      "institutional": 1,
      "sector": 1
    }
  },
  
  "timing": {
    "check_frequency": "weekly",
    "review_frequency": "monthly",
    "rebalance_frequency": "quarterly"
  }
}
Confidence Scoring:
Starting: 10%

Increases:
+ 15% if SEC Edgar API connected (official filings)
+ 10% if fundamentals data (Alpha Vantage) connected
+ 10% if insider trading data connected (smart money indicator)
+ 5% per 5 successful stock picks (positive track record)
+ 10% if context file is detailed (shows investment philosophy)

Decreases:
- 5% for each stock pick that loses money
- 10% if recommendation is wrong on thesis (bought, thesis broke, took loss)
- 15% if holding loser > 6 months (didn't exit when thesis broke)
- Can drop to 0% if consecutive bad picks

Threshold to go live:
- Minimum: 50%
- Recommended: 70%
- Safe: 85%+

AGENT #2: INDEX AGENT
Purpose: Build a diversified core portfolio and rebalance smartly based on market conditions.
What It Does:

Holds core index positions (VOO for US, VXUS for international, BND for bonds)
Monitors market valuation and macro conditions quarterly
If market overvalued: Increase bonds, reduce stocks
If market undervalued: Increase stocks, reduce bonds
Can add tactical sector funds for diversification
Rebalances quarterly or when allocation drifts > 10%
Enters "semi-active" period during rebalance to monitor execution

Core Holdings (Default Allocation):
Base Allocation (70% stocks / 20% bonds / 10% cash):

CORE HOLDINGS:
- 60-70% VOO (Vanguard S&P 500)
- 15-20% VXUS (Vanguard Total International)
- 15-25% BND (Vanguard Total Bond)
- 0-5% VGIT/Cash (Short-term preservation)

TACTICAL OVERLAYS (Added if appropriate):
- Photonics Fund (if diversifying into emerging themes)
- Sector funds (if market conditions favor certain sectors)
- International ex-US (if USD weakness)
Decision Logic:
QUARTERLY REBALANCE CYCLE:

Quarter starts (Jan 1, Apr 1, Jul 1, Oct 1)
    ↓
MARKET VALUATION CHECK:
"Is the market overvalued, fairly valued, or undervalued?"
- Metric 1: Shiller P/E ratio
- Metric 2: Market cap to GDP
- Metric 3: Fed Model (earnings yield vs bond yield)
    ↓
MACRO CONDITIONS CHECK:
"Is the economy healthy, mixed, or showing weakness?"
- GDP growth trajectory
- Inflation level
- Fed policy (raising/holding/cutting rates)
- Unemployment level
    ↓
DECISION TREE:

If Market OVERVALUED + Macro WEAKENING:
    → DEFENSIVE rebalance
    → 50% stocks / 40% bonds / 10% cash
    → EXAMPLE: Sell VOO at $450, buy BND at $75
    → Reason: Reduce downside risk when valuations stretched

If Market FAIRLY VALUED + Macro STABLE:
    → NEUTRAL rebalance
    → 65% stocks / 25% bonds / 10% cash
    → EXAMPLE: Maintain current allocation, minor trim
    → Reason: Balanced approach, no major changes

If Market UNDERVALUED + Macro IMPROVING:
    → AGGRESSIVE rebalance
    → 80% stocks / 15% bonds / 5% cash
    → EXAMPLE: Sell BND, buy VOO + VXUS
    → Reason: Maximize upside when valuations attractive

    ↓
TACTICAL DIVERSIFICATION:
"Should we add any sector or theme allocations?"
- If photonics sector booming: +5% to photonics fund
- If healthcare aging: +3% to healthcare fund
- If tech leading: +2% to tech fund (but already in VOO)
    ↓
EXECUTION PLAN:
- Place orders (if approved)
- Enter SEMI-ACTIVE monitoring (1 hour/day)
- Monitor fills
- Confirm all positions executed
    ↓
EXIT SEMI-ACTIVE:
- After 1 week or all executions complete
- Return to passive monitoring
    ↓
NEXT QUARTER:
- Recheck conditions
- Repeat cycle
Entry Logic:
QUARTERLY REBALANCE TRIGGER
    ↓
VALUATION ASSESSMENT:
- Shiller P/E > 28 = Overvalued
- Shiller P/E 18-28 = Fair
- Shiller P/E < 18 = Undervalued
    ↓
MACRO ASSESSMENT:
- GDP growth > 3% + inflation stable = Good
- GDP growth 1-3% + inflation rising = Mixed
- GDP growth < 1% + unemployment rising = Weakening
    ↓
ALLOCATION DECISION:
- Overvalued + Weakening = 50/40/10
- Fair + Stable = 65/25/10
- Undervalued + Improving = 80/15/5
    ↓
DIVERSIFICATION DECISION:
- Any tactical allocations needed?
- Any sector over/underweighted?
    ↓
REBALANCE:
- Execute buys and sells
- Confirm all fills
    ↓
MONITORING:
- Weekly position check
- Monthly performance review
- Quarterly full rebalance

EXAMPLE SCENARIO:
Current: 70% VOO, 20% BND, 10% cash
Assessment: Market overvalued (P/E 32), recession risk rising
Decision: "Move to defensive allocation"
Action: Sell $70k VOO, buy $40k BND, keep $30k cash
New: 50% VOO, 40% BND, 10% cash
Result: Protected downside when market drops 20%
Exit Logic:
ONGOING MONITORING:
- Weekly: Drift check (is allocation staying in target?)
- Monthly: Performance review
- Quarterly: Full rebalance cycle

DRIFT EXIT:
"Allocation has drifted > 10% from target"
- Example: Target 70% stocks, now at 78% (stocks up)
- Action: Rebalance back to 70% (sell stocks, buy bonds)
- Automatically triggers when drift exceeds threshold

TACTICAL EXIT:
"Tactical allocation thesis is wrong"
- Example: Added 5% to photonics, but sector declined
- Action: Exit photonics position, redeploy to core
- Reviews quarterly if thesis still valid

OPPORTUNITY EXIT:
"Better allocation found"
- Example: International markets now undervalued
- Action: Increase VXUS allocation at expense of VOO
- Redeploy within context of overall allocation

EMERGENCY EXIT:
"Market crash or recession confirmed"
- Example: Market down 25%+, recession started
- Action: Shift 20% to bonds/cash to stabilize portfolio
- Protects remaining capital from further downside
Context File Example:
AGENT: Index Fund Manager
STYLE: Strategic Asset Allocation with Tactical Adjustments
GOAL: Build diversified wealth safely over time

CORE HOLDINGS (Always Own):
- 60-70% VOO (US large cap, broad exposure)
- 15-20% VXUS (International, currency diversification)
- 15-25% BND (Bonds, stability, income)
- 0-5% Cash (Flexibility, emergency)

REBALANCE SCHEDULE:
- Quarterly (Jan 1, Apr 1, Jul 1, Oct 1)
- OR when allocation drifts > 10% from target
- Execution: 1-week semi-active monitoring period

VALUATION FRAMEWORK:
OVERVALUED: Shiller P/E > 28
- Action: Shift 10-15% from stocks to bonds
- Reason: Reduce downside in overheated market

FAIR VALUE: Shiller P/E 18-28
- Action: Maintain balanced allocation
- Reason: No major changes needed

UNDERVALUED: Shiller P/E < 18
- Action: Shift 10-15% from bonds to stocks
- Reason: Buy on weakness, maximize upside

MACRO CONDITIONS FILTER:
Check BEFORE rebalancing:
- Fed policy (is it accommodative or restrictive?)
- GDP growth (is economy accelerating or slowing?)
- Inflation (is it stable, rising, or falling?)
- Unemployment (is it rising or falling?)

If economy weakening: Shift to defensive (more bonds)
If economy strengthening: Shift to offensive (more stocks)

TACTICAL DIVERSIFICATION (Add when theme is strong):
- Photonics Fund: If semiconductor/optical demand surging
- Healthcare Fund: If aging demographics driving growth
- International Developed: If Europe/Japan fundamentals improving
- Emerging Markets: If China/India growth accelerating

Max tactical allocation: 10% (rest is core 90%)

POSITION SIZING:
- VOO: 55-75% (largest core holding)
- VXUS: 10-20% (international diversification)
- BND: 10-30% (stability and bonds)
- Tactical: 0-10% (opportunistic)
- Cash: 0-5% (dry powder)

HOLD PERIODS:
- Core: Forever (VOO, VXUS, BND are hold-forever positions)
- Tactical: 1-3 years (until thesis plays out or reverses)

REBALANCE RULES:
1. Always buy the weakest asset (opportunity to buy low)
2. Always sell the strongest asset (lock in gains)
3. Don't try to time the market perfectly
4. Stick to the plan even when emotions run high

EXAMPLE REBALANCE:
Current: 72% VOO, 18% BND, 10% cash (drift from 70/20/10)
Action: Sell $20k VOO, buy $20k BND
New: 70% VOO, 20% BND, 10% cash (back to target)
Reason: Rebalanced when stocks got too high, bought bonds on weakness

RISK MANAGEMENT:
- Max loss target: -30% in severe bear market
- Recovery plan: When down 30%, shift to 40% bonds for stability
- Minimum hold period: 5+ years (don't sell into panic)
- Max trading: 4x per year (quarterly rebalances only)
Configuration:
json{
  "agent_name": "Index Fund Manager",
  "enabled": true,
  "room": "long_term_investment",
  "strategy": "strategic_asset_allocation",
  "context_file": "contexts/index_fund_manager.txt",
  
  "core_holdings": {
    "voo": { "ticker": "VOO", "target_allocation": 65, "min": 55, "max": 75 },
    "vxus": { "ticker": "VXUS", "target_allocation": 18, "min": 10, "max": 25 },
    "bnd": { "ticker": "BND", "target_allocation": 20, "min": 10, "max": 30 },
    "cash": { "ticker": "VMFXX", "target_allocation": 2, "min": 0, "max": 5 }
  },
  
  "tactical_overlays": {
    "enabled": true,
    "max_allocation": 10,
    "available_funds": ["PSYK", "PHOTONICS", "VGT", "VXUS", "VCNS"]
  },
  
  "valuation_metrics": {
    "shiller_pe_overvalued": 28,
    "shiller_pe_fair": [18, 28],
    "shiller_pe_undervalued": 18,
    "rebalance_drift_threshold": 10
  },
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 300,
    "semi_active_period_hours": 1,
    "semi_active_monitoring_frequency_minutes": 5
  },
  
  "timing": {
    "rebalance_frequency": "quarterly",
    "check_frequency": "weekly",
    "review_frequency": "monthly",
    "rebalance_months": [1, 4, 7, 10]
  },
  
  "data_sources": {
    "valuation": "shiller_pe_api",
    "macro": "fred_api",
    "prices": "broker_api",
    "news": "finnhub"
  }
}

Meta Agents (Control & Monitoring)
AGENT: RISK MANAGEMENT AGENT
Purpose: Monitor all agents and summarize portfolio health in real-time.
What It Does:

Tracks all agents' P&L, win rates, confidence scores
Identifies underperforming agents
Calculates portfolio-wide metrics
Alerts user to problems
Recommends actions (pause agent, reduce allocation, etc.)
Can authorize Bodyguard Agent to take action

Outputs:
RISK DASHBOARD (Professional, Business-Style Summary):

PORTFOLIO OVERVIEW
├─ Total Capital: $100,000
├─ Current P&L: +$12,340 (+12.3%)
├─ 30-Day Return: +4.2%
├─ YTD Return: +18.5%
├─ Max Drawdown: -8.3%
└─ Sharpe Ratio: 1.4

BY ROOM
├─ Day Trading: +$2,100 (+2.1%) - 3 agents active
├─ Sector Trading: +$5,200 (+5.2%) - 2 agents active
└─ Long-Term Investing: +$5,040 (+5.0%) - 2 agents active

AGENT SCORECARDS
├─ News Agent: +$1,200 ✅ Confidence: 72% Wins: 68% (35/51)
├─ Energy Trader: +$3,100 ✅ Confidence: 81% Wins: 62% (18/29)
├─ Stock Picker: +$4,000 ✅ Confidence: 88% Wins: 75% (12/16)
├─ Index Agent: +$1,240 ✅ Confidence: 95% Wins: 100% (1/1)
└─ Tech Trader: -$1,160 ⚠️ Confidence: 35% Wins: 40% (6/15) - UNDERPERFORMING

ALERTS
⚠️  Tech Trader losing streak: 5 consecutive losses (-1.1% total)
⚠️  Confidence dropped to 35% (was 55% last week)
⚠️  Recommend: Pause agent, review context file, adjust entry signals
✅ Energy Trader: Outperforming (+15% vs market +8%)
✅ Stock Picker: All positions profitable (rare achievement)

RECOMMENDATIONS
1. IMMEDIATE: Pause Tech Trader (losing streak, low confidence)
2. SHORT-TERM: Review Tech context file (signals are wrong)
3. LONG-TERM: Diversify away from tech sector (single sector bet)
Configuration:
This agent is always active. No configuration needed.

AGENT: BODYGUARD AGENT
Purpose: Execute control commands from Risk Agent or user.
What It Does:

Receives pause/resume commands
Receives position close commands
Receives allocation rebalance commands
Executes with cool UI animation
Logs all actions
Confirms with user before major actions (if user approved risk agent)

UI Animation:
When Bodyguard pauses an agent:

Agent on warroom floor receives handcuffs animation
Gentle "click" sound effect
Pause icon above agent's head (red circle with pause symbol)
Agent stops moving/animating
Note appears: "Paused by Risk Agent - Reason: Losing streak"


Prebuilt Agents (Ready-to-Deploy)
Users can immediately "hire" these agents without configuration:
Day Trading Prebuilt Agents:

✅ News Agent (all market-moving announcements)
✅ Technical Signals Agent (RSI, MACD, MA crosses)
✅ Prediction Market Agent (Kalshi/Polymarket)
Earnings Surprise Trader (beats/misses, available Phase 2)
Crypto News Trader (Bitcoin, Ethereum)
Volatility Spike Trader (VIX > 25)

Sector Trading Prebuilt Agents:

✅ Energy Sector Trader (XLE rotation)
✅ Technology Sector Trader (XLK rotation)
✅ Healthcare Sector Trader (XLV rotation)
✅ Finance Sector Trader (XLF rotation)
✅ Materials Sector Trader (XLB rotation)
✅ Consumer Sector Trader (XLY/XLP rotation)
✅ Utilities Sector Trader (XLU rotation)

Long-Term Investment Prebuilt Agents:

✅ Stock Picker Agent (value investing, mini-agents, DCF)
✅ Index Fund Agent (diversified core portfolio, tactical adjustments)
Dividend Growth Investor (high-yield, growing dividends, Phase 2)
Growth Investor (high-growth stocks, Phase 2)
Value Investor (deep value, contrarian, Phase 2)


Context File Reference
Context File Structure
What is a Context File?
A context file is a plain English (or JSON) document that tells an agent "Here are the rules I want you to follow."
Two Formats:
Format 1: Plain English (Recommended)
AGENT: [Name]
ROOM: [day_trading / sector_trading / long_term_investment]
ASSETS: [What does this agent trade?]

ENTRY RULES:
- Rule 1
- Rule 2
- Rule 3

EXIT RULES:
- Rule 1
- Rule 2
- Rule 3

POSITION SIZING:
- [Constraints]

RISK MANAGEMENT:
- [Limits]

NOTES:
[Any special instructions]
Format 2: JSON (For Advanced Users)
json{
  "agent_name": "...",
  "room": "...",
  "entry_rules": [ {...}, {...} ],
  "exit_rules": [ {...}, {...} ],
  ...
}
Variables Available in Context Files
PRICE DATA:
${PRICE} - Current price
${PRICE_5D_CHANGE} - 5-day price change %
${PRICE_52W_HIGH} - 52-week high
${PRICE_52W_LOW} - 52-week low

TECHNICAL INDICATORS:
${RSI_14} - RSI(14)
${MACD} - MACD value
${MACD_SIGNAL} - MACD signal line
${MA_20} - 20-day moving average
${MA_50} - 50-day moving average
${MA_200} - 200-day moving average
${BOLLINGER_UPPER} - Upper Bollinger Band
${BOLLINGER_LOWER} - Lower Bollinger Band
${ATR} - Average True Range (volatility)
${VOLUME} - Current volume
${VOLUME_AVG_20} - 20-day average volume

FUNDAMENTAL DATA:
${PE_RATIO} - Price to Earnings ratio
${PB_RATIO} - Price to Book ratio
${DIVIDEND_YIELD} - Dividend yield %
${DEBT_EQUITY} - Debt to Equity ratio
${ROE} - Return on Equity
${EPS_GROWTH} - EPS growth rate
${REVENUE_GROWTH} - Revenue growth rate

ACCOUNT DATA:
${ACCOUNT_BALANCE} - Total account balance
${ACCOUNT_CASH} - Available cash
${ACCOUNT_POSITIONS} - Number of open positions
${PORTFOLIO_RETURN} - YTD portfolio return %
${PORTFOLIO_DRAWDOWN} - Current max drawdown %

MARKET DATA:
${MARKET_IS_OPEN} - True/False
${SECTOR_RELATIVE_STRENGTH} - Sector vs S&P 500 performance
${VIX} - Volatility index
${MARKET_BREADTH} - Advance/decline ratio

TIME:
${TIME_OF_DAY} - HH:MM format
${DAY_OF_WEEK} - Monday, Tuesday, etc.
${DAYS_UNTIL_EARNINGS} - If earnings coming

Confidence Score System
How Confidence Scoring Works
Purpose: Confidence score helps users decide when to switch from paper trading to live trading.
Starting Confidence:

10% (context file only, no APIs)

Increases:

+5% for each connected data source (Finnhub, SEC Edgar, etc.)
+10% for paid API connections (Bloomberg, Refinitiv)
+2% per 5 consecutive winning trades (earned confidence through performance)
+5% when user improves context file (shows commitment)
+10% when context file is detailed and specific

Decreases:

-2% for each losing trade
-10% for consecutive losses (3+ in a row)
-20% when auto-paused by Risk Agent (losing streak)
Resets to 50% when unpaused and retried (fresh start)

Scoring Formula (Simplified):
Confidence = Base (10%) 
           + API_Score (0-30%)
           + Performance_Score (0-40%)
           + Context_Score (0-20%)
           
Examples:
- Context only: 10%
- + 1 API: 15%
- + 2 APIs: 20%
- + 3 APIs + paid: 30%
- + 10 winning trades: 50%
- + Context improvement: 55%
- - 5 consecutive losses: 35%
Thresholds:
ConfidenceRecommendation0-30%Don't go live yet (too risky)30-50%Can go live, but very cautious (1-2% position sizes)50-70%Safe to go live (full position sizes)70-85%Good to go (trust the agent)85-100%Excellent (agent is proven)

Agent Customization Guide
How Much Can Users Customize Agents?
By Agent Type:
AgentCustomizable?How?News Agent✅ YESEdit context file (what news = trade?)Tech Signals✅ YESEdit context file (which signals?)Prediction✅ YESEdit context file (what events?)Sector Traders✅ YESEdit context file (sector rules)Stock Picker⚠️ SOMEWHATEdit context file (valuation targets)Index Agent⚠️ SOMEWHATEdit allocation targets, rebalance frequency
How to Customize (User Workflow)
Step 1: Select Agent Type

Example: "Energy Sector Trader"

Step 2: Modify Context File (Main Way)

Edit: Entry rules
Edit: Exit rules
Edit: Position sizing
Edit: Data sources to monitor

Step 3: Configure Settings (JSON)

Execution mode (autonomous vs approval)
Position size limits
Frequency
Timeframes

Step 4: Test in Paper Trading

Run for 3+ days
Monitor results
Adjust context if needed
Repeat until confident

Step 5: Go Live

Switch to live mode
Monitor closely
Be ready to pause if underperforming


Conflict Resolution
What If Two Agents Want to Buy the Same Stock?
Example:

News Agent wants to buy NVDA (earnings surprise)
Tech Sector Trader wants to buy NVDA (sector strength)

Resolution:
✅ Both can have positions simultaneously

News Agent: 1% account (quick trade, days hold)
Tech Trader: 5% account (sector bet, weeks hold)
Total: 6% account in NVDA (diversification maintained)

Why this works:

Different timeframes (no conflict)
Different entry logic (different theses)
Complementary positioning (both right, both profit)

What If Agents Conflict on Exit?
Example:

Tech Sector Trader says: HOLD (sector still strong)
Stock Picker Agent says: SELL (valuation reached)

Resolution:

Each agent independently manages its position
Tech Trader exits when sector breaks
Stock Picker exits when valuation reached
No forced interaction


Example Agent Deployments
Example Portfolio 1: Conservative Beginner
Day Trading Room (5% capital):
├─ News Agent (biotech news, small positions)
└─ Disabled: Prediction Agent (learn first)

Sector Trading Room (15% capital):
├─ Energy Sector Trader (10%)
└─ Utilities Sector Trader (5%)

Long-Term Investment Room (80% capital):
├─ Index Fund Agent (70%)
└─ Stock Picker Agent (10%, only undervalued stocks)

Meta:
├─ Risk Management Agent (always active)
└─ Bodyguard Agent (needs user approval to pause)

CONFIDENCE TARGETS:
- News Agent: Start at 50%, target 70% before scaling
- Sector Traders: Start at 60% (2 APIs connected), target 75%
- Stock Picker: Start at 65% (fundamentals API), target 85%
- Index Agent: Start at 95% (just execution, proven strategy)
Example Portfolio 2: Active Trader
Day Trading Room (30% capital):
├─ News Agent (all sectors)
├─ Technical Signals Agent (momentum)
└─ Prediction Agent (sports + politics)

Sector Trading Room (40% capital):
├─ Energy Sector Trader (10%)
├─ Technology Sector Trader (15%)
├─ Healthcare Sector Trader (10%)
└─ Finance Sector Trader (5%)

Long-Term Investment Room (30% capital):
├─ Index Fund Agent (20%)
└─ Stock Picker Agent (10%, growth + value mix)

Meta:
├─ Risk Management Agent (alert on any underperformance)
└─ Bodyguard Agent (auto-pause if drawdown > -15%)

CONFIDENCE TARGETS:
- All day traders: Target 75%+ before scaling
- All sector traders: Target 80%+ before scaling
- Stock picker: Target 85%+ before scaling
- Index agent: Target 95%+ (boring but works)

APPENDIX: FULL AGENT TAXONOMY (QUICK REFERENCE)
DAY TRADING AGENTS (Fast, News/Signals/Predictions)
├─ News Agent ✅ Prebuilt
├─ Technical Signals Agent ✅ Prebuilt
├─ Prediction Market Agent ✅ Prebuilt
├─ Earnings Surprise Trader (Phase 2)
└─ [More options in Prebuilt]

SECTOR TRADING AGENTS (Medium, Sector Rotation)
├─ Energy Sector Trader ✅ Prebuilt
├─ Technology Sector Trader ✅ Prebuilt
├─ Healthcare Sector Trader ✅ Prebuilt
├─ Finance Sector Trader ✅ Prebuilt
├─ Materials Sector Trader ✅ Prebuilt
├─ Consumer Sector Trader ✅ Prebuilt
└─ Utilities Sector Trader ✅ Prebuilt

LONG-TERM AGENTS (Slow, Fundamental)
├─ Stock Picker Agent ✅ Prebuilt
├─ Index Fund Agent ✅ Prebuilt
└─ [More options in Phase 2]

META AGENTS (Control & Monitoring)
├─ Risk Management Agent ✅ Always Active
└─ Bodyguard Agent ✅ Always Active

TOTAL IN MVP: 11 Prebuilt Agents (+ 2 Meta)
CUSTOMIZABLE: All via context files

END OF AGENTS.MD
Last Updated: June 2026

Version: 1.0 (MVP)

Status: Ready for Implementation
