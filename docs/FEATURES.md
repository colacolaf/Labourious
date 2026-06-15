FEATURES.md
The Complete Feature Set for Labourious
This document describes every feature being built, when it's being built, and how it works.

TABLE OF CONTENTS

Feature Overview
MVP Features (v1.0)
Phase 2 Features
Phase 3 Features
Core Features (Detailed)
Control Room & Portfolio Management
Warroom & UI Customization
Time Scheduling System
Risk Management System
Data Sources & API Integrations
Monitoring & Analytics
User Settings & Configuration


Feature Overview
Labourious is built on these core pillars:

Agent System — Autonomous AI traders with human oversight
Warroom Interface — Visual, real-time monitoring
Control Room — Portfolio management and configuration
Risk Management — Safety guardrails and auto-pause
Data Integration — Real-time market data from brokers and APIs
Transparency — See exactly why agents trade


MVP Features (Version 1.0)
MUST-HAVE FEATURES FOR LAUNCH
2.1 AGENT SYSTEM (Core)
Feature: Autonomous AI Agents

Users can "hire" prebuilt agents
Agents read context files to make decisions
Agents execute trades via brokers
Agents log all actions for audit trail

Status: MVP ✅
Includes:

3 prebuilt day trading agents (News, Signals, Prediction)
7 prebuilt sector trading agents (one per S&P sector)
2 prebuilt long-term agents (Stock Picker, Index)
Risk Management meta-agent
Bodyguard meta-agent


Feature: Paper Trading Mode

New agents start in paper trading (3-day minimum)
Uses live market data, simulates execution
No real money at risk
Shows what agent WOULD do

Status: MVP ✅
Configuration:

Initial balance: $10,000 - $1,000,000 (user-configurable)
Slippage: 0-1% (user-configurable)
Commission: $0-20 per trade (user-configurable)
Duration: 3 days to infinity


Feature: Confidence Score System

Each agent has a confidence score (10-100%)
Score improves with connected APIs and successful trades
Score decreases with losses
User can't go live below 50% (recommended 70%+)
Auto-increases when user improves context files

Status: MVP ✅
How It Works:
Base: 10% (just context file)
+ APIs: +5-10% each connected API
+ Performance: +2-5% per 5 winning trades
+ Context Quality: +10% for detailed context files
- Losses: -2% per losing trade, -10% for streaks
- Auto-pause: Resets to 50% when unpaused

Thresholds:
50% = "Can go live, very cautious"
70% = "Safe to go live"
85% = "Excellent, trust the agent"

2.2 WARROOM INTERFACE
Feature: 2D Isometric Warroom

Visual representation of trading rooms
Agents shown as sprites/cards in each room
Click agent to open Inspector panel
Real-time animation of agent activity

Status: MVP ✅
Features:

3 default rooms: Day Trading, Sector Trading, Long-Term Investment
Agents appear as working at desks when active
Agents roam when inactive (idle animation)
Pause symbol ( ⏸ ) above agent's head when forcibly paused
Smooth camera pan/zoom controls
50+ agents supported without lag


Feature: Agent Inspector Panel

Right-side panel showing agent details
Tabs: Overview, Trades, Rules, Performance, Settings
One-click approve/reject for human-in-loop trades
Shows last 10 trades with entry/exit prices and reasons

Status: MVP ✅
Tabs:

Overview — Current P&L, win rate, active positions, confidence score
Trades — Recent trades, filter by date/symbol/status
Rules — Display context file, rule-firing history
Performance — Daily returns, Sharpe ratio, max drawdown
Settings — Edit execution mode, position size, data sources


Feature: Agent Animation & UI Feel

Agents work at desks when active (typing, monitoring)
Agents roam/walk when inactive
Pause animation: Handcuffs appear on agent (cool visual)
Trade notification: Agent briefly highlights
Win/loss indicator: Green ✅ / Red ❌ glow on agent card

Status: MVP ✅ (Visual Polish)

2.3 CONTROL ROOM
Feature: Control Room (Portfolio Dashboard)

New room in warroom (accessible via button)
Shows all agents and their stats
Configure global settings
Reallocate capital between rooms
"Hire" new agents

Status: MVP ✅
Capabilities:

Agent Hiring

Browse prebuilt agent templates
See storage cost, API requirements
One-click deploy
Decide allocation for new agent


Capital Reallocation

Sliders for each room (Day: 10%, Sector: 20%, Long-Term: 70%)
Drag to adjust
Shows impact: "Moving 5% from Day to Long-Term"
Requires all trading to pause for adjustment


Global Settings

Default execution mode (autonomous vs approval)
Approval timeout (5-30 seconds per agent type)
Paper trading toggle
Drawdown limit (auto-pause if portfolio down -X%)


Risk Summary

Total P&L by room
Total P&L by agent
Which agents are profitable/unprofitable
Which agents are paused and why




Feature: Control Room UI Design
┌─ CONTROL ROOM ─────────────────────────────────────┐
│                                                      │
│ PORTFOLIO AT A GLANCE                               │
├─────────────────────────────────────────────────────┤
│ Total Capital: $100,000                              │
│ Current P&L: +$12,340 (+12.3%) ✅                   │
│ Max Drawdown: -8.3%                                  │
│ 30-Day Return: +4.2%                                 │
├─────────────────────────────────────────────────────┤
│ CAPITAL ALLOCATION (Drag sliders to adjust)         │
│                                                      │
│ Day Trading:        ├─────●──────────┤ 10%         │
│ Sector Trading:     ├─────────────●──┤ 30%         │
│ Long-Term Invest:   ├─────────────────●┤ 60%       │
│                                                      │
│ [APPLY CHANGES]                                     │
├─────────────────────────────────────────────────────┤
│ AGENTS (All 11 shown)                               │
│                                                      │
│ Room          Agent              P&L      Conf  Act │
│ ───────────────────────────────────────────────────│
│ Day Trading   News Agent         +$1,200  72%   ✅ │
│ Day Trading   Tech Signals       -$180    55%   ✅ │
│ Sector Tr.    Energy Trader      +$3,100  81%   ✅ │
│ Sector Tr.    Tech Trader        -$1,160  35%   ❌ │
│ Long-Term     Stock Picker       +$4,000  88%   ✅ │
│ Long-Term     Index Agent        +$1,240  95%   ✅ │
│ ...                                                  │
│                                                      │
├─────────────────────────────────────────────────────┤
│ [+ HIRE NEW AGENT]  [GLOBAL SETTINGS]  [RISK MODE] │
└─────────────────────────────────────────────────────┘

2.4 RISK MANAGEMENT
Feature: Automatic Agent Pausing

Agent tracks its own performance continuously
If losing streak detected (3+ consecutive losses), agent auto-pauses
Agent generates diagnosis: "Why did I fail? What do I need?"
User can review, fix context, and resume

Status: MVP ✅
Pause Triggers:

Consecutive losing trades: 3-5 in a row (configurable)
Confidence below threshold (< 35%)
Risk limit hit (portfolio drawdown > user limit)

Recovery Process:

Agent pauses automatically
Risk Management Agent sends diagnosis to user
User reviews: "What went wrong?"
User options:

Edit context file and resume
Adjust data sources and resume
Delete agent entirely
Leave paused




Feature: Portfolio Drawdown Limits

User sets max portfolio drawdown (e.g., -20%)
If portfolio down more than limit: Bodyguard auto-pauses ALL agents
Halts all trading, preserves remaining capital
Prevents catastrophic losses

Status: MVP ✅
Configuration:

Soft limit: -15% (warning, user can override)
Hard limit: -25% (auto-pause, no override)
Recovery: When portfolio recovers to -10%, agents can resume


Feature: Risk Management Agent Dashboard

Professional, business-style summary
Shows: Total P&L, P&L by room, P&L by agent
Lists underperforming agents
Recommends actions: "Pause this agent", "Review this context file"
Can recommend Bodyguard take action (if user approved)

Status: MVP ✅

2.5 EXECUTION MODES
Feature: Human-in-Loop Execution

Agent makes decision
Sends to user for approval
User has 5-30 seconds to approve/reject
If no response: Trade auto-rejected (safe default)
Best for: Day trading and sector trading

Status: MVP ✅
User Experience:
[AGENT DECISION]
┌─ NEWS ALERT ─────────────────────────────────┐
│                                               │
│ News Agent detected FDA approval              │
│ Agent wants to BUY BIOPSY (biotech stock)    │
│                                               │
│ Confidence: 78%                               │
│ Position Size: 1.5% account = $1,500         │
│                                               │
│ Reasoning: "FDA approved cancer drug,       │
│ bullish for BIOPSY, high confidence in       │
│ positive news sentiment"                      │
│                                               │
│ [✅ APPROVE] [❌ REJECT] [⏱ 28 sec left]     │
│                                               │
└─────────────────────────────────────────────────┘

Feature: Autonomous Execution

Agent makes decision and executes immediately
No user approval needed
Subject to position size limits
Best for: Long-term investment (lower frequency)

Status: MVP ✅
Configuration:

Per-agent: "Execution mode = Autonomous"
Position size limit: Max 5% per position
Account limit: Max 50% of capital in autonomous agents


Feature: Risk-Based Execution

Low-risk trades (small position, high confidence): Auto-execute
High-risk trades (large position, low confidence): Wait for approval

Status: MVP ✅
Logic:
Risk Score = (1 - Confidence%) * Position_Size%

If Risk Score < 2: Auto-execute (low risk)
If Risk Score > 5: Wait for approval (high risk)
If Risk Score 2-5: Ask user based on trade type

2.6 PAPER TRADING & BACKTESTING
Feature: Paper Trading Mode

All agents can run in paper trading
Uses live market data, simulates execution
3-day minimum for new agents
Shows what agent WOULD do without risking money

Status: MVP ✅
How It Works:
Agent Decision → Simulated Order → Simulated Fill
                       ↓
           (No actual money moved)
                       ↓
           Update P&L, Log Trade

Feature: Backtesting (CLI Tool)

Command: labourious backtest agent.json --start=2024-01-01 --end=2024-06-30
Runs agent on historical data
Generates report: Total return, win rate, Sharpe ratio, drawdown
Helps validate strategy before going live

Status: MVP ✅
Output Example:
BACKTEST RESULTS: Energy Sector Trader
────────────────────────────────────────
Period: 2024-01-01 to 2024-06-30
Total Trades: 12
Winning Trades: 8 (67%)
Losing Trades: 4 (33%)

Total Return: +18.5%
Average Trade Return: +1.54%
Best Trade: +8.2%
Worst Trade: -4.1%

Sharpe Ratio: 1.3
Max Drawdown: -12.4%
Recovery Time: 8 days

Verdict: ✅ Profitable, good consistency
Ready to paper trade, then go live

2.7 BROKER INTEGRATION
Feature: Secure Broker Connection

User connects broker accounts via encrypted vault
Credentials never transmitted to cloud
Supports: Interactive Brokers, Kraken, Coinbase (v1.0)
Extensible for more brokers

Status: MVP ✅
Brokers Supported (v1.0):

✅ Interactive Brokers (stocks, options, futures)
✅ Kraken (Bitcoin, Ethereum, altcoins)
✅ Coinbase (Bitcoin, Ethereum, select altcoins)

Future Brokers (Phase 2+):

Alpaca (stocks, crypto)
Binance (crypto)
TD Ameritrade (stocks)
Others on request


Feature: Encrypted Credential Vault

User sets vault password during setup (8+ characters)
API keys encrypted with AES-256 + PBKDF2
Keys never leave user's machine
Encrypted backup created for recovery

Status: MVP ✅

2.8 DATA SOURCES & API INTEGRATIONS
Feature: Real-Time Market Data

Broker APIs provide live price data
Free alternatives: Alpha Vantage, Finnhub, Yahoo Finance
User can connect additional APIs (free or paid)
Agents fetch data at configured frequencies

Status: MVP ✅
Included (Free APIs):

Alpha Vantage (free: 5 calls/min, 500/day)
Finnhub (free: basic news, 60 calls/min)
Yahoo Finance (free: historical data)
Broker APIs (included with account)

Paid Options (User Can Connect):

Bloomberg Terminal (professional data)
Refinitiv (institutional research)
FRED API (macro data, free)
SEC Edgar (filings, free)


2.9 TIME SCHEDULING SYSTEM
Feature: Flexible Agent Scheduling

Each agent runs on user-defined schedule
Day traders: Real-time (every 1-5 minutes)
Sector traders: Daily (once per day)
Long-term: Weekly (once per week)

Status: MVP ✅
Configuration:
json{
  "agent_name": "Energy Trader",
  "timing": {
    "check_frequency": "daily",
    "check_time": "09:30 EST",
    "trading_hours": {
      "start": "09:30",
      "end": "16:00",
      "timezone": "EST"
    },
    "skip": {
      "market_opens": true,
      "holidays": true,
      "fed_announcements": true,
      "major_events": true
    }
  }
}

Feature: User-Configurable Timing

Users can customize check frequency per agent
Can set trading windows (e.g., "only trade 10am-3pm")
Can blacklist periods (e.g., "skip earnings season")
Can skip holidays and market closures

Status: MVP ✅

2.10 REAL-TIME MONITORING & NOTIFICATIONS
Feature: Live P&L Dashboard

Shows portfolio value updating in real-time
Shows agent performance in real-time
Shows trade execution status
WebSocket connection for instant updates

Status: MVP ✅

Feature: Notifications

Trade executed: Notification to user
Agent paused: Alert with reason
Portfolio milestone: "$50k reached!", "Up 10%!"
Risk alerts: "Drawdown at -15%, approaching limit"

Status: MVP ✅
Notification Channels:

In-app (browser/Electron notifications)
Optional: Email alerts (Phase 2)
Optional: SMS alerts (Phase 2)


2.11 WARROOM CUSTOMIZATION
Feature: Agent Animation Customization

User can adjust agent movement speed
User can adjust animation style (fast/medium/slow)
User can change agent appearance (avatar, color, theme)
Purely cosmetic, doesn't affect trading

Status: MVP ✅
Options:

Movement Speed: 0.5x (slow), 1x (normal), 2x (fast)
Appearance: Default, Dark, Retro, Custom colors
Animation: Active (agents work), Idle (agents roam)


2.12 SETTINGS & CONFIGURATION
Feature: Setup Wizard

Runs on first launch
Step 1: Welcome & intro
Step 2: Connect broker
Step 3: Choose LLM (Ollama or Cloud)
Step 4: Set initial capital allocation
Step 5: Hire first agents

Status: MVP ✅
Time: 5-10 minutes total

Feature: Settings Panel

Broker connections: Add/remove/edit
LLM settings: Choose local vs cloud, API keys
Global settings: Approval timeout, drawdown limits
User preferences: Theme, language, notifications

Status: MVP ✅

Phase 2 Features
These are valuable but not required for v1.0 launch.
Phase 2.1 Advanced Agents
Feature: Dividend Growth Investor

Focuses on high-yield, growing-dividend stocks
Monitors dividend cut risks
Rebalances quarterly
Holds 3-5 years minimum

Estimated Build Time: 1-2 weeks

Feature: Growth Investor

Focuses on high-growth tech/innovation stocks
Less value-focused, more momentum-aware
Holds 1-2 years
Higher risk, higher return potential

Estimated Build Time: 1-2 weeks

Feature: Earnings Surprise Trader

Trades stocks after earnings beats/misses
Similar to News Agent but earnings-specific
Quick in, quick out (same day)

Estimated Build Time: 1 week

Phase 2.2 Advanced Features
Feature: Context File UI Builder

Drag-and-drop interface to build context files
No coding required
Generates JSON or text automatically
Validates rules before saving

Estimated Build Time: 2-3 weeks

Feature: Mobile Companion App (iOS/Android)

View warroom on phone
Approve/reject trades remotely
See P&L and agent status
Get notifications

Estimated Build Time: 4-6 weeks

Feature: Email & SMS Notifications

Trade executed: Email summary
Agent paused: SMS alert
Daily digest: "Your agents made $X today"

Estimated Build Time: 1-2 weeks

Feature: Advanced Backtesting

Optimization mode: Test different parameters
Walk-forward testing: Validate on out-of-sample data
Comparative analysis: Test multiple agents simultaneously
Export to CSV/PDF

Estimated Build Time: 2-3 weeks

Feature: Agent Marketplace

Users share custom agents with community
GitHub-based agent library
One-click import shared agents
Rate and review agents

Estimated Build Time: 3-4 weeks

Phase 2.3 Broker Additions

Alpaca (stocks, options, crypto)
Binance (crypto)
TD Ameritrade (stocks)

Estimated Build Time: 1 week per broker

Phase 3 Features
Phase 3.1 Advanced LLM Integration
Feature: Claude/GPT Cloud LLM Support

Users connect OpenAI or Anthropic API
Agents use cloud LLM for better reasoning
Cost: ~$0.001-0.01 per decision
Better decision quality for complex strategies

Status: Phase 3

Feature: LLM Model Selection UI

User chooses: Ollama (free/local) or Claude (paid/cloud)
Can switch per agent
Shows cost estimate per month
Shows reasoning quality differences

Status: Phase 3

Phase 3.2 Advanced Analytics
Feature: Correlation Analysis

Analyze correlation between agents
Show which agents diversify each other
Recommend combinations

Status: Phase 3

Feature: Attribution Analysis

"What made my portfolio gain/lose today?"
Break down returns by agent
Show contribution of each trade

Status: Phase 3

Feature: Risk Factor Analysis

Decompose portfolio risk into factors
Identify concentration risks
Recommend rebalancing

Status: Phase 3

Phase 3.3 Multi-User & Collaboration
Feature: Multi-User Support

Family/team can share same Labourious instance
Separate logins, separate portfolios
Parent account controls permissions

Status: Phase 3

Feature: Agent Sharing & Collaboration

Create shared agent libraries per team
Collaborative editing of context files
Version control (git-like)

Status: Phase 3

Core Features (Detailed)
5.1 PAPER TRADING MODE
What It Does:
Allows users to test agents with live market data but no real money.
How It Works:
1. User creates agent and sets to Paper Trading
2. Agent runs normally (fetches data, makes decisions)
3. Instead of real broker → simulated order
4. Simulated execution at current market price
5. P&L calculated but not real
6. After 3 days (or whenever) → user approves live
Configuration:
json{
  "paper_trading": {
    "enabled": true,
    "duration_days": 3,
    "initial_balance": 100000,
    "slippage_percent": 0.1,
    "commission_per_trade": 10
  }
}
Slippage & Commission:

Slippage: Simulates bid/ask spread (default 0.1%)
Commission: Simulates trading costs (default $10/trade)
These factors influence paper trading returns realistically

Mandatory for New Agents:

All new agents MUST paper trade 3 days minimum
Cannot skip paper trading
Confidence score starts at 10%
Switching to live requires 50%+ confidence (recommended 70%+)


5.2 CONFIDENCE SCORE SYSTEM
What It Is:
A metric (10-100%) that shows how trustworthy an agent is.
Components:
ComponentWeightHow It WorksAPI Quality30%More/better APIs = higher scoreContext Quality20%Detailed context files = higher scorePerformance40%Winning trades = higher scoreExperience10%More trades = higher score
Examples:
New Agent (context only):
- Base: 10%
- Total: 10%
- Recommendation: Paper trade, don't go live yet

Agent after 1 API added:
- Base: 10%
- + Finnhub API: +5%
- Total: 15%
- Recommendation: Still paper trade

Agent after 5 winning trades:
- Previous: 15%
- + Performance: +10%
- Total: 25%
- Recommendation: Still paper trade

Agent after context file improved:
- Previous: 25%
- + Context quality: +10%
- Total: 35%
- Recommendation: Getting there, keep going

Agent after 2 APIs + 10 wins + good context:
- Base: 10%
- + APIs: +10%
- + Context: +15%
- + Performance: +20%
- Total: 55%
- Recommendation: Can go live (minimum threshold)

Agent with all APIs + 30 wins + excellent context:
- Total: 85%
- Recommendation: Excellent, high confidence
How Confidence Affects User Behavior:
10-30%: "Don't use yet, keep improving"
30-50%: "You can paper trade this"
50-70%: "Can go live, but small positions"
70-85%: "Good to go, normal positions"
85-100%: "Excellent, can trust with larger positions"
Resetting Confidence:

If agent auto-paused: Resets to 50%
User can manually improve context to re-earn confidence
Each improvement adds back to score
If agent fails repeatedly: Can drop to 0%


5.3 RISK MANAGEMENT AGENT
What It Does:
Monitors all other agents and alerts user to problems.
Monitoring:
Real-Time Monitoring:
├─ P&L per agent
├─ Win rate per agent
├─ Confidence score per agent
├─ Portfolio drawdown
├─ Room-level performance
└─ User-set risk limits

Triggers:
├─ Agent losing streak (3+ losses)
├─ Agent confidence below 35%
├─ Portfolio drawdown exceeds limit
├─ Agent hasn't traded in 30 days (inactive?)
└─ User-defined custom alerts
Reporting:
RISK MANAGEMENT DASHBOARD (Business Professional Style)

PORTFOLIO HEALTH
├─ Total P&L: +$12,340 (+12.3%) ✅
├─ 30-Day Return: +4.2%
├─ Max Drawdown: -8.3%
└─ Sharpe Ratio: 1.4

BY ROOM
├─ Day Trading: +$2,100 (+2.1%)
├─ Sector Trading: +$5,200 (+5.2%)
└─ Long-Term: +$5,040 (+5.0%)

AGENT STATUS
├─ Active agents: 9/11 ✅
├─ Paused agents: 1/11 (Tech Trader, losing streak)
├─ Winning agents: 8/9 (89%)
└─ Losing agents: 1/9 (11%)

TOP PERFORMERS
├─ Stock Picker: +$4,000 (conf: 88%)
├─ Energy Trader: +$3,100 (conf: 81%)
└─ Index Agent: +$1,240 (conf: 95%)

UNDERPERFORMERS
├─ Tech Trader: -$1,160 (conf: 35%) ⚠️

ALERTS
├─ Tech Trader: 5-trade losing streak
├─ Recommend: Pause agent, review context
└─ Risk: -1.2% to portfolio if continues

5.4 BODYGUARD AGENT
What It Does:
Executes control commands (pause, resume, reallocate) with cool UI.
Actions It Can Take:
1. PAUSE AGENT
   ├─ On Risk Agent recommendation
   ├─ On user command
   ├─ Animation: Handcuffs appear on agent
   ├─ Agent stops moving
   ├─ Pause icon (⏸) above head

2. RESUME AGENT
   ├─ On user request
   ├─ After context file fixed
   ├─ Agent animation resumes

3. FORCE-CLOSE POSITION
   ├─ On Risk Agent command (with user approval)
   ├─ When portfolio drawdown exceeds limit
   ├─ Closes all open positions immediately
   ├─ Logs reason: "Portfolio protection"

4. REALLOCATE CAPITAL
   ├─ Move capital between rooms
   ├─ Close positions in source room
   ├─ Open positions in destination room
   ├─ Requires all trading to pause

5. HIRE NEW AGENT
   ├─ Deploy prebuilt agent
   ├─ Set initial configuration
   ├─ Allocate capital
UI Animations:
PAUSE ANIMATION:
Agent standing at desk
→ Handcuffs appear (✤ symbol)
→ Agent grayed out
→ Pause icon (⏸) floats above head
→ Agent stops moving
→ Status: "PAUSED - Losing streak detected"

RESUME ANIMATION:
Agent grayed out
→ Handcuffs disappear
→ Agent brightens
→ Agent returns to normal animation
→ Status: "ACTIVE - Context file updated"

FORCE-CLOSE ANIMATION:
Agent at desk
→ Red alert flashes
→ Agent briefly stops
→ Money symbol ($) flies from agent
→ Agent position closes
→ Status: "POSITION CLOSED - Portfolio protection"

Control Room & Portfolio Management
6.1 Portfolio Summary
PORTFOLIO OVERVIEW
─────────────────────────
Total Capital: $100,000
Account Value: $112,340 (+12.3%)
Cash On Hand: $8,500
Margin Used: $0 (0%)

Time Period: YTD 2024
Days Since Inception: 182 days
Annualized Return: 24.6% (on pace)

Max Drawdown: -8.3% (Jan 15, 2024)
Time to Recover: 12 days
Current Streak: +4 days (winning)

6.2 Capital Allocation Sliders
ROOM ALLOCATION (Drag Sliders to Rebalance)

Day Trading Room      [====●=========] 10% ($10,000)
Sector Trading Room   [=========●=====] 30% ($30,000)
Long-Term Investment  [==============●] 60% ($60,000)

[APPLY REBALANCING]

REBALANCING IMPACT:
- Sell: $5,000 from Day Trading
- Buy: $5,000 to Long-Term
- New: Day 5%, Sector 30%, Long-Term 65%
- Estimated Execution Time: 2 minutes

6.3 Agent Management Table
AGENT MANAGEMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Room           Agent              P&L      % Return  Conf  Status
───────────────────────────────────────────────────────────
Day Trading    News Agent         +$1,200  +10%      72%   ✅ Active
Day Trading    Tech Signals       -$180    -1.8%     55%   ✅ Active
Sector Tr.     Energy Trader      +$3,100  +10.3%    81%   ✅ Active
Sector Tr.     Tech Trader        -$1,160  -3.9%     35%   ⏸ Paused
Long-Term      Stock Picker       +$4,000  +13.3%    88%   ✅ Active
Long-Term      Index Agent        +$1,240  +6.2%     95%   ✅ Active

ACTIONS (Click agent row):
├─ [👁 INSPECT] → Open inspector panel
├─ [⏸ PAUSE] → Pause agent
├─ [📊 STATS] → Detailed performance
└─ [⚙️ SETTINGS] → Edit configuration

6.4 Global Risk Settings
GLOBAL RISK SETTINGS
────────────────────────────────────────
Portfolio Max Drawdown:  [20 %] ← Hard limit
                         [15 %] ← Warning level

Auto-Pause Triggers:
├─ ✅ Consecutive losses (set to 3)
├─ ✅ Confidence below 35%
├─ ✅ Portfolio drawdown > limit
└─ ☐ Custom metric (disabled)

Default Execution Mode:
├─ ☐ Autonomous (all agents, any time)
├─ ✅ Human-in-Loop (agents wait 30 sec)
└─ ☐ Risk-Based (mix of above)

Approval Timeout:
├─ Day Traders:     [ 10 ] seconds
├─ Sector Traders:  [ 30 ] seconds
└─ Long-Term:       [300 ] seconds (5 minutes)

[SAVE SETTINGS]

Warroom & UI Customization
7.1 Agent Animation Speed
MOVEMENT SPEED
└─ Slow (0.5x)   - Agents move slowly, easy to watch
└─ Normal (1x)   - Default speed
└─ Fast (2x)     - Agents move quickly, live feel
└─ Off (0x)      - Agents stay still (minimal animation)
7.2 Agent Appearance
AGENT AVATAR
├─ Default (colorful sprites)
├─ Dark Mode (dark backgrounds, light agents)
├─ Retro (pixelated 1980s style)
├─ Minimal (simple shapes)
└─ Custom (user uploads SVG)

AGENT COLORS
├─ Day Traders: Blue theme
├─ Sector Traders: Green theme
├─ Long-Term: Gold theme
├─ Or: User custom colors per agent
7.3 Warroom Theme
THEME OPTIONS
├─ Light (white background, dark text)
├─ Dark (dark background, light text)
├─ High Contrast (for accessibility)
└─ Retro (1980s ASCII-style, fun)
7.4 Real-Time Animation Preferences
AGENT BEHAVIOR
├─ Active: Agents work at desks (typing, monitoring)
├─ Idle: Agents roam/walk around (when no trading)
├─ Minimal: Just show cards, no animation
├─ Advanced: Show trade execution animations

Time Scheduling System
8.1 Frequency Options
DAY TRADERS:
├─ Real-time (check market every 1-5 minutes)
├─ High frequency (every 5-30 minutes)
└─ Medium frequency (every 1-4 hours)

SECTOR TRADERS:
├─ Daily (once per trading day, usually 09:30 or 15:00)
├─ Twice daily (morning and afternoon check)
└─ Intraday (every 4 hours)

LONG-TERM:
├─ Weekly (same day/time each week)
├─ Monthly (first/last day of month)
└─ Quarterly (specific quarter starts: Jan 1, Apr 1, etc.)
8.2 Market Hours & Blackouts
TRADING WINDOWS:
├─ Stocks: 09:30 - 16:00 EST (market hours)
├─ Crypto: 24/7 (always open)
├─ Options: 09:30 - 16:00 EST (market hours)

AUTO-SKIPS (Agent Won't Run):
├─ Market Holidays (Thanksgiving, Christmas, etc.)
├─ Market Closed Days (weekends, half-days)
├─ Fed Announcement Days (high volatility)
├─ Major Economic Data Releases (jobs report)
├─ First 15 minutes of market open (chaotic)
├─ Last 15 minutes of market close (thin volume)

USER-DEFINED BLACKOUTS:
├─ "Skip earnings season (April-May)"
├─ "Don't trade during my vacation (June 1-7)"
├─ "Avoid trading Mondays"

Risk Management System
9.1 Automatic Agent Pausing
PAUSE TRIGGERS:
├─ Consecutive losing trades (3-5 configurable)
├─ Confidence score below threshold (< 35%)
├─ Portfolio drawdown > user limit
├─ Agent hasn't traded in 30 days (inactive)
└─ User-defined custom triggers
9.2 Portfolio Drawdown Controls
SOFT LIMIT (-15%):
├─ Warning notification sent
├─ User can override and continue
├─ Recommends review of strategy

HARD LIMIT (-25%):
├─ Auto-pause ALL agents
├─ No override available
├─ Preserves remaining capital
├─ User must review before resuming
9.3 Position Size Limits
PER-AGENT LIMITS:
├─ Max position: 3-7% per trade (configurable)
├─ Max concurrent: 3-5 positions (configurable)
└─ Max sector exposure: 20-25% (configurable)

ACCOUNT-LEVEL LIMITS:
├─ Max leverage: 1:1 (no margin, default)
├─ Max concentration: No single stock > 10%
└─ Max sector: 25% per sector

Data Sources & API Integrations
10.1 Free APIs (Included)
APIPurposeRate LimitCostAlpha VantageStock data, technicals5 calls/minFreeFinnhubNews, company data60 calls/minFreeYahoo FinanceHistorical dataUnlimitedFreeSEC EdgarSEC filingsUnlimitedFreeFREDMacro dataUnlimitedFreeBroker APIsReal-time quotes, ordersPer brokerIncluded

10.2 Paid APIs (Optional, User Connects)
APIPurposeCostUse CaseBloomberg TerminalProfessional news, data$20k+/yearSerious tradersRefinitivInstitutional research$10k+/yearProfessional investorsFactSetDeep financial data$10k+/yearEquity researchersMorningstarFund/stock data$200+/monthAnalysts

10.3 User-Configurable Data Sources
json{
  "agent_name": "Stock Picker",
  "data_sources": {
    "market_data": "alpha_vantage",
    "news": "finnhub",
    "fundamentals": "alpha_vantage",
    "sec_filings": "edgar",
    "macro": "fred",
    "optional": [
      {
        "name": "bloomberg_terminal",
        "api_key": "[user_provides]",
        "enabled": true
      }
    ]
  }
}

Monitoring & Analytics
11.1 Agent Performance Metrics
PER-AGENT METRICS
─────────────────────────────
Total P&L: +$4,200
Return %: +14.0%
Number of Trades: 18
Winning Trades: 12 (67%)
Losing Trades: 6 (33%)
Win Rate: 66.7%
Average Winner: +$485
Average Loser: -$189
Profit Factor: 2.1

Risk Metrics:
Max Drawdown: -8.3%
Sharpe Ratio: 1.2
Sortino Ratio: 1.8
Calmar Ratio: 1.7

Confidence Score: 78%
Status: ✅ Active
Last Trade: 2 hours ago

11.2 Portfolio Dashboard
PORTFOLIO DASHBOARD
─────────────────────────────
Total Value: $112,340
Cash: $8,500
Invested: $103,840
YTD Return: +12.3%
30-Day Return: +4.2%
Max Drawdown: -8.3%

By Room:
├─ Day Trading: +$2,100 (+2.1%)
├─ Sector Trading: +$5,200 (+5.2%)
└─ Long-Term: +$5,040 (+5.0%)

By Agent:
├─ Stock Picker: +$4,000 (35.7%)
├─ Energy Trader: +$3,100 (27.7%)
├─ Index Agent: +$1,240 (11.1%)
├─ News Agent: +$1,200 (10.7%)
└─ [Others]: +$1,800 (14.1%)

11.3 Trade History & Filters
TRADE HISTORY
──────────────────────────────────────────────────
Date       Agent              Symbol  Type Qty  Entry    Exit    P&L      %
─────────────────────────────────────────────────
2024-06-10 News Agent        BIOPSY  BUY  100  $45.20  $46.80  +$160    3.5%
2024-06-09 Energy Trader     XLE     BUY  200  $82.10  $84.40  +$460    2.8%
2024-06-08 Stock Picker      AAPL    BUY  50   $192    $195    +$150    1.6%
2024-06-07 Tech Trader       XLK     BUY  100  $52.30  $50.80  -$150   -2.9%
2024-06-06 Index Agent       VOO     BUY  10   $445.30 $447.10 +$18     0.4%

FILTERS:
├─ By Agent
├─ By Room
├─ By Symbol
├─ By Date Range
├─ By Status (winning, losing, open)
└─ By Trade Type (buy, sell)

[EXPORT TO CSV] [EXPORT TO PDF]

User Settings & Configuration
12.1 Broker Configuration
CONNECTED BROKERS
──────────────────────────────
✅ Interactive Brokers (IB3456789)
   Status: Connected
   Account Type: Individual
   Last Connection: 2 minutes ago
   
✅ Kraken (kraken_api_key)
   Status: Connected
   Account Type: Spot Trading
   Last Connection: Just now
   
☐ Coinbase
   Status: Not Connected
   [+ CONNECT COINBASE]

12.2 LLM Configuration
LLM SELECTION
──────────────────────────────
Current LLM: Ollama (Local)
Model: Mistral 7B
Status: ✅ Running on localhost:11434
Response Time: 1-3 seconds per decision

[SWITCH TO CLAUDE API]
  └─ Cost: ~$0.001-0.01 per decision
  └─ Better reasoning for complex strategies
  └─ Requires API key

[SWITCH TO GPT-4]
  └─ Cost: ~$0.01-0.03 per decision
  └─ Strongest reasoning available
  └─ Requires OpenAI API key

12.3 Backup & Recovery
ENCRYPTED BACKUPS
──────────────────────────────
Last Backup: Today at 14:32
Status: ✅ Successful
Location: ~/.labourious/backups/

Backup Contents:
├─ Encrypted API keys
├─ Agent configurations
├─ Context files
├─ Trade history
└─ User preferences

[DOWNLOAD BACKUP]  [AUTO-BACKUP: Toggle]  [RESTORE FROM BACKUP]

FEATURES SUMMARY TABLE
FeatureMVPPhase 2Phase 3Agent System (11 prebuilt agents)✅Paper Trading Mode✅Confidence Score System✅Warroom Interface (2D isometric)✅Agent Inspector Panel✅Control Room✅Risk Management Agent✅Bodyguard Agent✅Encrypted Vault✅Broker Integration (3 brokers)✅Time Scheduling System✅Real-Time Notifications✅Warroom Customization✅Backtesting CLI✅Context File UI Builder✅Mobile App✅Email/SMS Alerts✅Agent Marketplace✅Multi-Broker Support (6+ brokers)✅Cloud LLM Support (Claude/GPT)✅Multi-User/Team Support✅Advanced Analytics✅Collaborative Agent Development✅

IMPLEMENTATION ROADMAP
Sprint 1-2: Core Infrastructure (Weeks 1-4)

✅ Project setup (Electron, React, TypeScript)
✅ Database schema (agents, trades, configurations)
✅ Broker API integrations (IB, Kraken, Coinbase)
✅ Encrypted vault implementation
✅ Basic LLM integration (Ollama)

Sprint 3-4: Agent System (Weeks 5-8)

✅ News Agent implementation
✅ Technical Signals Agent
✅ Prediction Market Agent
✅ Sector Trader template (all 7)
✅ Agent execution engine

Sprint 5-6: Warroom & UI (Weeks 9-12)

✅ 2D isometric warroom rendering
✅ Agent animations and interactions
✅ Inspector panel
✅ Control Room dashboard
✅ Warroom customization

Sprint 7-8: Long-Term Agents (Weeks 13-16)

✅ Stock Picker Agent (with mini-agents)
✅ Index Agent
✅ Risk Management Agent
✅ Bodyguard Agent
✅ Confidence scoring system

Sprint 9-10: Risk & Monitoring (Weeks 17-20)

✅ Risk management system
✅ Auto-pause mechanisms
✅ Performance monitoring
✅ Real-time notifications
✅ Trade logging & history

Sprint 11-12: Testing & Polish (Weeks 21-24)

✅ Comprehensive testing
✅ Security audit
✅ Performance optimization
✅ User documentation
✅ Beta launch preparation


END OF FEATURES.MD
Last Updated: June 2026

Version: 1.0 (MVP)

Status: Ready for Implementation

QUICK START FOR DEVELOPERS

Read AGENTS.md first — Understand what agents are and how they work
Read FEATURES.md second — Understand what features need to be built
Start with MVP features — Don't build Phase 2/3 yet
Use the configuration examples — They're production-ready JSON
Follow the roadmap — Sprint structure is proven for this scope

Questions? Refer back to specific sections or ask during sprint planning.
