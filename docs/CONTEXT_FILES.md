Context Files Reference
Complete guide to writing context files that Labourious agents follow.

What Are Context Files?
A context file is your trading rulebook. It tells an agent exactly how you want it to trade.
Agents read context files and use them to make decisions:
Agent Reads Data → Reads Context File → Asks LLM → Executes Trade
Two Formats:

Plain English (recommended for non-coders)
JSON (for programmers and advanced users)


Plain English Format (Recommended)
Basic Structure
AGENT NAME: [name]
ROOM: [day_trading | swing_trading | long_term_investment | custom]
ASSETS: [comma-separated list of symbols]
BROKER: [kraken | interactive_brokers | coinbase]

ENTRY RULES:
- Rule 1: [condition]
- Rule 2: [condition]

EXIT RULES:
- Rule 1: [condition]
- Rule 2: [condition]

POSITION SIZING:
- Max position: [%]
- Max concurrent: [number]

RISK MANAGEMENT:
- Stop loss: [%]
- Take profit: [%]

NOTES:
[Any additional instructions or context]
Complete Example: News Trader
AGENT NAME: FDA News Trader
ROOM: day_trading
ASSETS: CRSP, BIOPSY, MRNA, GILD, AMGN (biotech stocks)
BROKER: interactive_brokers

ENTRY RULES:
- Major FDA approval or rejection announced
- Announcement from official source (not rumor)
- Company market cap > $1 billion (liquid enough to trade)
- No pending SEC investigations

EXIT RULES:
- Price moved 5% from entry (captured initial spike)
- 15 minutes elapsed (news reaction fades)
- Volume dries up below 50% of average
- Stop loss: -3% (news thesis wrong)

POSITION SIZING:
- Small biotech (< $5B market cap): 0.5% of account
- Mid biotech ($5-20B): 1% of account
- Large biotech (> $20B): 1-2% of account
- Max concurrent positions: 3

RISK MANAGEMENT:
- Stop loss: -3%
- Take profit: 70% of expected move (don't wait for 100%)

NOTES:
News trading has high variance. Winning trades typically make 2-4%
in minutes, but quick stops are also common. Key is capturing the
immediate reaction before market fully prices in the news.
Complete Example: Momentum Trader
AGENT NAME: Tech Momentum Swing Trader
ROOM: swing_trading
ASSETS: NVDA, TSLA, AMD, MSFT, GOOGL (high-beta tech)
BROKER: interactive_brokers

ENTRY RULES:
- RSI(14) < 30 (oversold) + RSI starting to rise
- OR: MACD crosses above signal line
- Confirmation: Volume > 20-day average
- Price > 50-day moving average (not a dead stock)

EXIT RULES:
- RSI > 70 (overbought) → sell full position
- OR: MACD crosses below signal line → sell
- OR: Price closes below 50-day MA → sell
- OR: Profit target reached (+10-15%)
- Stop loss: -5% from entry

POSITION SIZING:
- Position size: 1% of account per signal
- Max concurrent positions: 5
- Max position size: $5,000

RISK MANAGEMENT:
- Stop loss: -5%
- Take profit: +10-15%
- Max hold: 10 days (exit regardless)

NOTES:
This is a swing trader (2-5 day holds). Trade size is moderate.
Avoid trading first 30 minutes of market open (high noise).
Avoid trading during Fed announcements or major economic data.
Complete Example: Value Investor
AGENT NAME: Stock Picker - Value Investor
ROOM: long_term_investment
ASSETS: Any stock with strong fundamentals (focus on healthcare, financials, consumer)
BROKER: interactive_brokers

ENTRY RULES:
- Earnings growth > 5% annually
- P/E ratio < market average (< 18 if market is fair)
- Debt/Equity < 1.5 (manageable debt)
- Free cash flow positive and growing
- Dividend yield > 1.5% OR reinvestable profits

PREFERENCE RULES:
- Prefer dividend-paying companies
- Prefer stable industries over growth
- Prefer market leaders over startups

AVOID COMPLETELY:
- Pre-revenue biotech (too speculative)
- Money-losing tech startups
- Heavily leveraged companies (bankruptcy risk)
- Companies with accounting irregularities

EXIT RULES:
- P/E rises above 25 (valuation stretched)
- Dividend cut announced
- Profit target: +50%
- Loss limit: -25% (reassess thesis)

POSITION SIZING:
- New position: 3% of account
- Undervalued position: 5% of account
- Max per position: 7%
- Max sector exposure: 25%
- Max total positions: 15-25

REBALANCE FREQUENCY:
- Weekly: Check for major news
- Monthly: Review P&L
- Quarterly: Full re-analysis, add/trim/exit

HOLD PERIOD:
- Minimum: 6 months (be patient)
- Target: 1-3 years (let thesis play out)
- Maximum: 5+ years (if thesis still valid)

NOTES:
This is a fundamentals-driven, value-investing approach. Patience is key.
Don't try to time the market perfectly. Buy good companies at reasonable
prices and hold for the long term.

JSON Format (For Programmers)
Basic Structure
json{
  "agent_name": "...",
  "room": "...",
  "assets": [...],
  "broker": "...",
  "entry_rules": [
    {
      "name": "...",
      "condition": "...",
      "confirmation": "...",
      "confidence": 0.0
    }
  ],
  "exit_rules": [
    {
      "name": "...",
      "condition": "...",
      "action": "..."
    }
  ],
  "position_sizing": {
    "position_size_percent": 0.0,
    "max_concurrent": 0,
    "max_position_size": 0
  },
  "risk_management": {
    "stop_loss_percent": 0.0,
    "take_profit_percent": 0.0
  },
  "notes": "..."
}
Complete Example: Technical Signals
json{
  "agent_name": "Technical Signals Trader",
  "room": "swing_trading",
  "assets": ["NVDA", "TSLA", "AMD", "MSFT"],
  "broker": "interactive_brokers",
  "entry_rules": [
    {
      "name": "RSI Oversold",
      "condition": "${RSI_14} < 30",
      "confirmation": "${RSI_RISING} == true",
      "confidence": 0.7
    },
    {
      "name": "MACD Crossover",
      "condition": "${MACD} > ${MACD_SIGNAL}",
      "confirmation": "${VOLUME_SPIKE} == true",
      "confidence": 0.75
    },
    {
      "name": "Price Above MA",
      "condition": "${PRICE} > ${MA_50}",
      "confidence": 0.5
    }
  ],
  "exit_rules": [
    {
      "name": "RSI Overbought",
      "condition": "${RSI_14} > 70",
      "action": "sell_full_position"
    },
    {
      "name": "MACD Crossover Down",
      "condition": "${MACD} < ${MACD_SIGNAL}",
      "action": "sell_full_position"
    },
    {
      "name": "Take Profit",
      "condition": "${PROFIT_PERCENT} > 10",
      "action": "sell_full_position"
    },
    {
      "name": "Stop Loss",
      "condition": "${LOSS_PERCENT} < -5",
      "action": "sell_full_position"
    },
    {
      "name": "Time Exit",
      "condition": "${DAYS_HELD} > 10",
      "action": "sell_full_position"
    }
  ],
  "position_sizing": {
    "position_size_percent": 1.0,
    "max_concurrent_positions": 5,
    "max_position_size": 5000,
    "scaling_by_confidence": false
  },
  "risk_management": {
    "stop_loss_percent": -5.0,
    "take_profit_percent": 10.0,
    "max_hold_days": 10,
    "trailing_stop_percent": 0
  },
  "notes": "Medium-term momentum trader. Avoid market open first 30 minutes."
}

Variables Available in Context Files
Price & Technical Data
VariableMeaningRange${PRICE}Current price0.01 - ∞${PRICE_5D_CHANGE}5-day price change %-100 - ∞${PRICE_52W_HIGH}52-week highprice value${PRICE_52W_LOW}52-week lowprice value${PRICE_ABOVE_MA20}Price > 20-day MAtrue/false${MA_20}20-day moving averageprice value${MA_50}50-day moving averageprice value${MA_200}200-day moving averageprice value${RSI_14}RSI(14)0-100${RSI_RISING}RSI trending uptrue/false${MACD}MACD value-∞ - ∞${MACD_SIGNAL}MACD signal line-∞ - ∞${BOLLINGER_UPPER}Upper Bollinger Bandprice value${BOLLINGER_LOWER}Lower Bollinger Bandprice value${ATR}Average True Range0 - ∞${VOLUME}Current volume0 - ∞${VOLUME_AVG_20}20-day average volume0 - ∞${VOLUME_SPIKE}Volume > 150% of avgtrue/false
Fundamental Data
VariableMeaning${PE_RATIO}Price to Earnings ratio${PB_RATIO}Price to Book ratio${DIVIDEND_YIELD}Dividend yield %${DEBT_EQUITY}Debt to Equity ratio${ROE}Return on Equity %${EPS_GROWTH}EPS growth rate %${REVENUE_GROWTH}Revenue growth rate %
Account Data
VariableMeaning${ACCOUNT_BALANCE}Total account balance${ACCOUNT_CASH}Available cash${ACCOUNT_POSITIONS}Number of open positions${PORTFOLIO_RETURN}YTD portfolio return %${PORTFOLIO_DRAWDOWN}Current max drawdown %
Time Data
VariableMeaningExample${TIME_OF_DAY}Current time"14:32" (2:32 PM)${DAY_OF_WEEK}Current day"Monday", "Tuesday", etc.${DAYS_UNTIL_EARNINGS}Days until earnings5${DAYS_HELD}Days this position open3

Condition Syntax
Simple Conditions
${RSI_14} < 30                  (less than)
${RSI_14} > 70                  (greater than)
${RSI_14} == 50                 (equals)
${PRICE} between 100 and 200    (range)
${PRICE} != 150                 (not equals)
Logical Operators
${RSI_14} < 30 AND ${VOLUME_SPIKE}
  → Both must be true

${RSI_14} < 30 OR ${MACD_CROSS_ABOVE}
  → Either one is true

NOT ${RECENT_LOSSES} > 3
  → Negation
Complex Conditions
(${RSI_14} < 30 AND ${VOLUME_SPIKE}) OR ${MACD_CROSS_ABOVE}
  → Entry if: (oversold AND volume spike) OR momentum crosses

${PRICE} > ${MA_50} AND ${MA_50} > ${MA_200}
  → Uptrend confirmation (price > 50-day > 200-day)
Time Conditions
time between 09:30 and 11:00        (only trade during window)
NOT Monday                          (skip Mondays)
NOT ${DAYS_UNTIL_EARNINGS} < 5      (avoid earnings week)
${DAYS_HELD} > 5                    (only exit if held 5+ days)

Position Sizing Strategies
Fixed Size
Max position: 2% of account
→ If account = $100k, each trade = $2k
Scaling by Confidence
Position size = confidence * 2%
→ Confidence 80% → 1.6% position
→ Confidence 40% → 0.8% position
Scaling by Volatility
Position size inversely proportional to ATR
→ High volatility → smaller position
→ Low volatility → larger position
Profit Scaling
First position: 1%
If winning: Add 0.5% more
Max position: 2%

Stop Loss & Take Profit Strategies
Fixed Percentages
Stop loss: -5%
Take profit: +15%
→ Exit if down 5% or up 15%
Indicator-Based
Stop loss: 1 ATR below entry
Take profit: 2 ATR above entry
→ Dynamic based on volatility
Time-Based
Hold for maximum 3 days, then exit
→ Automatic exit after holding period
Trailing
Trailing stop: 5% below highest price
→ Exit if profit drops 5% from peak
Hybrid
Initial stop: -5%
After +10% profit: Move stop to breakeven
After +15% profit: Trail by 3%
→ Protect profits while letting winners run

Common Mistakes & Solutions
Mistake 1: Rules Too Strict (No Trades)
WRONG:
BUY: RSI < 10 AND MACD < 0 AND price < MA200 AND earnings in 3 months
→ Too many conditions, almost never all true simultaneously
RIGHT:
BUY: RSI < 30 OR MACD crosses above signal line
→ Fewer conditions, more trade opportunities
Fix: Use OR instead of AND, relax thresholds

Mistake 2: Rules Too Loose (Too Many Trades)
WRONG:
BUY: price up 1%
→ Trades on any small move, loses money quickly
RIGHT:
BUY: price breaks 20-day high AND volume > 2x average
→ Confirmation signal filters out noise
Fix: Add confirmation signal, tighten thresholds

Mistake 3: Curve Fitting
WRONG:
BUY: RSI == 32.7 AND close == $145.89
→ Works on past data (you've memorized it), fails on new data
RIGHT:
BUY: RSI < 30 AND price breaks above 20-day MA
→ Uses logical rules, not memorized numbers
Fix: Use round numbers, use logic (not exact values), test on multiple timeframes

Mistake 4: Ignoring Risk
WRONG:
No stop loss defined
Position size = all available capital
→ One bad trade wipes out account
RIGHT:
Stop loss: -5%
Position size: 2% of account
Max 5 concurrent positions
→ Losses are limited and manageable
Fix: Always define stop loss and position sizing limits

Mistake 5: Too Many Indicators
WRONG:
Use 8 different indicators, all must align perfectly
→ Analysis paralysis, rarely triggers
RIGHT:
Use 2-3 key indicators, simple clear logic
→ Easy to understand, easy to execute
Fix: Simplify, test on historical data

Testing Your Context File
Step 1: Backtest
bashlabourious backtest your_agent.json --start=2024-01-01 --end=2024-06-30
Look for:

✅ Win rate > 40% (better than random)
✅ Sharpe ratio > 0.5 (good risk-adjusted returns)
✅ Max drawdown < 30% (acceptable risk)
✅ Enough trades to validate (10+ minimum)

Step 2: Paper Trade

Run in Paper Trading mode for 2-4 weeks
Monitor daily, review trades weekly
Look for: consistent performance, no surprise losses

Step 3: Small Live

Switch to Live with 1-5% of capital
Monitor closely for first week
Compare live results to paper trading

Step 4: Scale Up

Gradually increase position size
Only if live results match paper trading


Examples from Community
See examples/contexts/ folder for real context files:

news_trader.txt - FDA news trading (biotech)
tech_signals.txt - Technical momentum signals
energy_sector.txt - Sector rotation strategy
stock_picker.txt - Value investing fundamentals
index_fund.txt - Allocation management


Pro Tips

Keep it simple: 2-3 clear rules beat 10 complex rules
Test first: Always backtest before paper trading
Document your edge: Know WHY you expect the strategy to work
Avoid patterns in data: Use logic, not memorized numbers
Start small: Even good strategies lose money when sized wrong
Review regularly: Check performance monthly, adjust if needed
Version control: Save old context files, track improvements


Converting Between Formats
Plain English to JSON

Read through plain English version
Identify each rule as a JSON object
Convert condition strings to variable syntax
Test that JSON is valid

JSON to Plain English

Read JSON structure
Convert variables back to descriptions
Add context and explanations
Verify readability


Uploading to Labourious

Save context file as context_name.txt or .json
In Labourious, click "New Agent"
Paste or upload context file
Click "Validate"
Set configuration (position size, frequency, etc.)
Start in Paper Trading mode
Monitor and adjust


Getting Help

Syntax questions? Check the Variables section above
Logic questions? Review Common Mistakes section
Real examples? Browse examples/contexts/ folder
Feedback wanted? Share your context on GitHub Discussions


Ready to write your first context file? Pick a strategy you understand and follow the 5-step creation guide in AGENT_CREATION.md.
