Agent Creation Guide: Writing Your First Trading Rule
This guide teaches you to write trading rules that your AI agents will follow.

What is an Agent?
An agent is a combination of:

Context file — your trading rules in plain English or structured format
Configuration — which assets to trade, position size, execution mode
Room assignment — day trading room, swing trading room, or custom
When an agent runs, it:

Fetches live market data
Reads your context file to understand what you want
Asks the LLM: "Based on these rules, should we trade?"
Executes a trade or recommends one (depending on mode)
Core Concept: Context Files
A context file is the rulebook your agent follows. It can be:

Plain English (Recommended for Beginners)
AGENT NAME: Tech Value Investor
ROOM: Long-term Investing

ASSETS: AAPL, MSFT, NVDA, TSLA (stocks only)
MAX POSITION SIZE: $5,000 per stock
HOLDING PERIOD: 6+ months

RULES:
1. Buy if P/E ratio < market average AND RSI < 30
2. Only buy after 3 consecutive down days
3. Sell if P/E > industry average OR hit 50% gain
4. Never hold more than 5 positions at once
5. Avoid buying during market downturns > -3%

NOTES:
Watch for tech earnings announcements. Prefer companies 
with strong free cash flow and dividend history.
Structured JSON (For Advanced Users)
json
{
  "agent_name": "Tech Value Investor",
  "room": "long_term",
  "assets": ["AAPL", "MSFT", "NVDA", "TSLA"],
  "constraints": {
    "max_position_size": 5000,
    "max_positions": 5,
    "holding_period_min_days": 180,
    "avoid_market_drawdown_threshold": -0.03
  },
  "buy_rules": [
    {
      "condition": "pe_ratio < market_average AND rsi < 30",
      "confidence": 0.8
    },
    {
      "condition": "price_down_3_days",
      "confidence": 0.7
    }
  ],
  "sell_rules": [
    {
      "condition": "pe_ratio > industry_average",
      "confidence": 0.9
    },
    {
      "condition": "profit_percent > 50",
      "action": "take_profit"
    }
  ]
}
Building Your First Agent: 5 Steps
Step 1: Define Your Strategy Idea
Answer these questions:

What asset class? (stocks, crypto, options)
What's your edge? (momentum, value, mean reversion, sentiment)
How often do you trade? (daily, weekly, monthly)
What's your typical holding period? (hours, days, months)
Example:

Strategy: Crypto Momentum Trader
Asset: Bitcoin (BTC)
Edge: Buy when price breaks above 20-day high, sell on RSI overbought
Frequency: Daily checks
Holding: 2-5 days
Step 2: Write Your Rules in Plain English
Start simple. You can always add complexity later.

BAD (too vague):

Buy bitcoin when it's going up.
Sell when it's overbought.
GOOD (specific and testable):

BUY CONDITIONS:
1. Price closes above 20-day moving average
2. RSI(14) < 70 (not yet overbought)
3. Trading volume > 20-day average
4. Time: Only between 9am-4pm EST

SELL CONDITIONS:
1. Price closes below 20-day moving average, OR
2. RSI(14) > 80 (overbought), OR
3. Position up 15% (take profit)
4. Stop loss: Position down 5%
Step 3: Create Your Context File
Save this as contexts/my_first_agent.txt:

AGENT NAME: BTC Momentum Day Trader
ROOM: Day Trading
ASSET: BTC/USD (Bitcoin)
BROKER: Kraken

POSITION SIZING:
- Max position: $2,000 per trade
- Max concurrent positions: 2
- Risk per trade: 2% of account ($500)

ENTRY RULES:
Rule 1: Price breaks above 20-day moving average
  - Condition: Close > SMA(20)
  - Confirmation: Volume > 20-day average
  - Confidence: 0.7

Rule 2: Momentum signal
  - Condition: RSI(14) between 50-70
  - Condition: Price momentum > 0
  - Confidence: 0.8

Entry Logic: Trigger when Rule 1 AND Rule 2 both true

EXIT RULES:
Rule 1: Take profit at 15% gain
  - Condition: Profit % >= 15
  - Action: Sell 100% position

Rule 2: Stop loss at 5% loss
  - Condition: Loss % <= -5
  - Action: Sell 100% position

Rule 3: Intraday exit (close position by 3pm EST)
  - Condition: Time >= 15:00 EST
  - Action: Sell remaining position

EXIT PRIORITY: First true rule triggers exit

TIME CONSTRAINTS:
- Trading window: 9:00 AM - 4:00 PM EST
- Skip: Major news events, Fed announcements
- Skip: During market opens (high volatility first 30 min)

NOTES:
This agent is designed for active monitoring. Don't set to 
fully autonomous — approve trades for first 2 weeks of live trading.
Watch for gap opens that violate stop loss.
Step 4: Create Agent Configuration (JSON)
Save this as agents/btc_momentum.json:

json
{
  "id": "btc_momentum_001",
  "name": "BTC Momentum Day Trader",
  "enabled": true,
  "room": "day_trading",
  "context_file": "contexts/my_first_agent.txt",
  
  "execution": {
    "mode": "human_in_loop",
    "approval_timeout_seconds": 30,
    "auto_veto_on_news": true
  },
  
  "asset": {
    "symbol": "BTC/USD",
    "broker": "kraken",
    "asset_type": "crypto"
  },
  
  "capital": {
    "allocation_percent": 5,
    "max_position_size": 2000,
    "max_concurrent_positions": 2,
    "risk_per_trade_percent": 2
  },
  
  "timing": {
    "check_frequency": "every_5_minutes",
    "trading_hours": {
      "start": "09:00",
      "end": "16:00",
      "timezone": "EST"
    },
    "skip_events": ["fed_announcement", "major_earnings"]
  },
  
  "backtest": {
    "enabled": true,
    "start_date": "2024-01-01",
    "end_date": "2024-06-30",
    "initial_capital": 10000
  }
}
Step 5: Deploy and Test
In Labourious UI:

Go to your room (e.g., Day Trading)
Click "Add Agent"
Upload agents/btc_momentum.json
Verify context file loads correctly
Start in PAPER TRADING MODE
Watch for 1 week, review trades
If performance looks good, switch to LIVE mode
Common Agent Patterns
Pattern 1: Value Investor (Long-term)
STRATEGY: Buy undervalued stocks, hold for 6+ months

BUY SIGNALS:
- P/E ratio < 15
- Price/Book ratio < 2
- Dividend yield > 3%
- 52-week low within last 3 months

SELL SIGNALS:
- P/E ratio rises above 25
- Dividend cut announced
- Profit target: +50%
- Stop loss: -15%

REBALANCE: Quarterly (every 3 months)

ASSETS: VOO (S&P 500 ETF), VTI (Total market ETF), BND (Bond ETF)
ALLOCATION: 70% stocks, 30% bonds
Pattern 2: Momentum Trader (Swing, 2-5 days)
STRATEGY: Ride short-term trends, capture 10-20% moves

BUY SIGNALS:
- Price closes above 50-day moving average
- MACD crosses above signal line
- Volume surge (> 150% of average)

SELL SIGNALS:
- Price closes below 50-day MA (stop loss)
- Take profit: +15-20%
- After 5 days (exit regardless)

REBALANCE: Daily

ASSETS: High beta stocks (growth tech, small caps)
WATCH: IPOs, earnings surprises
Pattern 3: Mean Reversion (Day Trading)
STRATEGY: Buy oversold, sell overbought, capture quick swings

BUY SIGNALS:
- RSI(14) < 30 (oversold)
- Price touches lower Bollinger Band
- Volume spike down (capitulation)

SELL SIGNALS:
- RSI(14) > 70 (overbought)
- Price touches upper Bollinger Band
- Profit target: +3-5%
- Stop loss: -2%

REBALANCE: Intraday (multiple trades per day)

TIME WINDOW: 9:30am - 3:30pm EST only
SKIP: First 30 min (market open volatility)
Pattern 4: Crypto Arbitrage (Advanced)
STRATEGY: Exploit price differences across exchanges

BUY SIGNALS:
- Price on Exchange A < Price on Exchange B - 1%
- Check gas fees and withdrawal costs
- Slippage estimate < 0.5%

SELL SIGNALS:
- Execute immediately on other exchange
- Exit after profitable execution

REBALANCE: Real-time (seconds)

CONSTRAINTS:
- Min trade size: $500 (to beat fees)
- Max per trade: $10,000
- Watch: API rate limits
Advanced: Context File Syntax
Variables You Can Use
${MARKET_DATA.price}              - Current price
${MARKET_DATA.volume}             - Current volume
${MARKET_DATA.rsi}                - RSI(14)
${MARKET_DATA.macd}               - MACD value
${MARKET_DATA.moving_avg_20}      - 20-day MA
${MARKET_DATA.moving_avg_50}      - 50-day MA
${MARKET_DATA.bollinger_upper}    - Bollinger Band upper
${MARKET_DATA.bollinger_lower}    - Bollinger Band lower

${ACCOUNT.balance}                - Account balance
${ACCOUNT.positions}              - Open positions
${ACCOUNT.buying_power}           - Available capital
${ACCOUNT.margin_used}            - Margin ratio

${MARKET.is_open}                 - True/false
${MARKET.time_to_close}           - Minutes until close
${MARKET.volatility_index}        - VIX level
${MARKET.news_sentiment}          - Recent news sentiment
Condition Syntax
AND logic:
  Condition: price > 100 AND volume > 1000000 AND rsi < 30

OR logic:
  Condition: rsi < 30 OR macd_cross OR price_below_ma

NOT logic:
  Condition: NOT dividend_cut AND NOT earnings_soon

Comparisons:
  ${MARKET_DATA.price} > 150
  ${ACCOUNT.balance} < 50000
  ${MARKET_DATA.rsi} between 40 and 60
  ${MARKET_DATA.moving_avg_20} crosses ${MARKET_DATA.moving_avg_50}

Time conditions:
  time_of_day between 09:30 and 16:00
  day_of_week not in [Saturday, Sunday]
  minutes_since_entry > 60
Testing Your Agent Before Going Live
Step 1: Paper Trading (Simulated)
bash
labourious run-agent btc_momentum.json --paper-trading --days=30
Results:

Total return: +8.5%
Win rate: 62%
Sharpe ratio: 1.2
Max drawdown: -12%
Step 2: Backtesting (Historical Data)
bash
labourious backtest btc_momentum.json --start=2024-01-01 --end=2024-06-30
Step 3: Walk-Forward Testing (Continuous paper trading)
Run agent in paper mode for 2-4 weeks, review trades weekly.

Red Flags Before Going Live:
❌ Win rate < 40% (worse than random)
❌ Max drawdown > 30% (too risky)
❌ Sharpe ratio < 0.5 (bad risk-adjusted returns)
❌ Only a few trades (not enough data)
❌ Rule changed market conditions (overfitted)
Common Mistakes & How to Avoid Them
Mistake 1: Rules Too Tight (No Trades)
WRONG:
  BUY: RSI < 10 AND MACD crosses AND price below 200-day MA 
       AND earnings in 3 days AND ...

RIGHT:
  BUY: RSI < 30 OR MACD crosses (fewer conditions, more trades)
Mistake 2: Rules Too Loose (Too Many False Signals)
WRONG:
  BUY: Price up 1%

RIGHT:
  BUY: Price breaks 20-day high AND volume > 2x average
Mistake 3: Curve Fitting
WRONG:
  BUY: RSI < 32.7 (specific number based on past data)

RIGHT:
  BUY: RSI < 30 (round numbers, makes sense theoretically)
Mistake 4: Ignoring Risk
WRONG:
  No stop loss defined
  Position size = all available capital

RIGHT:
  Stop loss: -5% per position
  Position size: Max 2% of account per trade
Mistake 5: Over-Complicated Rules
WRONG:
  Buy: 14 different conditions across 8 indicators

RIGHT:
  Buy: 2-3 core conditions, simple enough to explain in 1 sentence
Managing Multiple Agents
Diversification example: "All-Weather Portfolio"

json
{
  "portfolio_name": "All-Weather",
  "allocation": {
    "long_term_value": { "agent": "value_investor", "percent": 60 },
    "swing_momentum": { "agent": "momentum_trader", "percent": 25 },
    "day_trading": { "agent": "mean_reversion", "percent": 10 },
    "cash_buffer": 5
  },
  "rebalance": "quarterly",
  "constraints": {
    "max_drawdown_portfolio": 0.25,
    "max_correlation": 0.5,
    "min_sharpe": 0.8
  }
}
Collaboration: Share Your Agents
Submit to Labourious Agent Library:

Test thoroughly (4+ weeks paper trading)
Document your edge (why does this work?)
Create example context file
Submit PR to examples/agents/
Community-submitted agents:

examples/agents/
├── btc_momentum_day_trader.json
├── tech_value_6month.json
├── sp500_mean_reversion.json
├── crypto_arbitrage.json
└── README.md (how to use each)
Next Steps
✅ You know how agents work!
📝 Write your first context file (start simple)
🧪 Test in paper trading (2-4 weeks minimum)
🚀 Deploy to live (small position first)
📊 Monitor and refine (weekly reviews)
Getting Help
Context file syntax questions? Check CONTEXT_FILES.md
Need an example agent? Browse examples/agents/
Agent not trading? See TROUBLESHOOTING.md
Want feedback? Open a PR in the Agent Library
Ready to create your first agent? Open Labourious and click "New Agent" in your room. 🚀


