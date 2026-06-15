Labourious
One-Liner
Labourious: A locally-hosted AI trading warroom where customizable agents autonomously execute trades across multiple strategies—with local LLM reasoning, encrypted credentials, and a retro-inspired interface that simplifies portfolio diversification.

What is Labourious?
Labourious is an open-source, locally-hosted AI trading platform that brings institutional-grade multi-strategy trading to your desktop. Download, configure, and watch AI agents work across different trading rooms—each optimized for a specific strategy (day trading, swing trading, long-term investing).
No cloud dependency. No exposed API keys. No complexity.
You control:

How much capital flows to each strategy (e.g., 80% long-term, 15% swing, 5% day trade)
The trading rules each agent follows (via context files you write or upload)
Whether agents execute autonomously or wait for your approval
Real-time monitoring from your desktop, phone, or any remote device


Core Features
🏟️ The Warroom: Retro-Inspired Multi-Room Interface

2D isometric view with depth perception — navigate rooms like a retro football stadium
Three default trading rooms (day trading, swing trading, long-term investing) + ability to create custom rooms
Click-on agents to inspect performance, view active trades, see rule-tracing, and toggle on/off
Live visual feedback — watch agents working in real-time as data flows in and trades execute

🤖 Intelligent Agents

Local LLM by default (Ollama) — agents reason about markets using your context files, offline and free
Optional cloud LLMs (Claude, GPT-4) — upgrade reasoning for complex strategies if desired
Context-driven trading — each agent reads a context file (your rules, research, signals) to make decisions
Multiple execution modes:

Autonomous (set and forget)
Human-in-the-loop (agent recommends, you approve)
Risk-based (conservative long-term, moderate swing, aggressive day trade)



🔐 Security First

Encrypted local vault for API keys (AES-256 at rest)
Zero cloud sync — keys never leave your machine
Open-source audit trail — community can verify encryption
Paper trading mode — test strategies risk-free before going live
Multi-user support — family/team with separate logins on same machine
Remote access — check agents from phone/another device (optionally)

📊 Deep Transparency

Performance dashboards — P&L, win rate, trade history per agent
Rule-tracing — see exactly why an agent made a trade (which context rules fired, signals matched)
Trade inspector — drill into any trade to understand entry/exit logic
Backtesting capability — test agents on historical data before deploying live

🎛️ Capital Allocation Made Simple

Pre-built portfolio suggestions (80/15/5, 60/30/10, etc.) tailored to risk profile
Custom allocation sliders — drag to rebalance between rooms
Rebalancing automation — system adjusts positions as strategies drift
Risk limits — set max drawdown, position size, leverage per agent

🚀 Multi-Strategy Execution

Day Trading Room — agents scan for intraday signals, execute on live data feeds
Swing Trading Room — agents hold positions 2-5 days, follow momentum/reversals
Long-Term Investing Room — agents follow fundamental rules, rebalance quarterly
Custom Rooms — define your own strategy tier (e.g., Options Trading, Crypto-focused)


Architecture at a Glance
┌─────────────────────────────────────────┐
│         Labourious Frontend             │
│  (React/Electron - Retro Warroom UI)    │
└────────────────┬────────────────────────┘
                 │
┌────────────────▼────────────────────────┐
│      Labourious Backend (Python)        │
│  - Agent orchestration                  │
│  - Broker API integration               │
│  - LLM routing (local/cloud)            │
│  - Trade execution & logging            │
└────────────────┬────────────────────────┘
                 │
        ┌────────┼────────┐
        │        │        │
   ┌────▼──┐ ┌──▼────┐ ┌─▼─────────┐
   │ Ollama│ │Broker │ │ Local DB  │
   │ (LLM) │ │ APIs  │ │(Encrypted)│
   └───────┘ └───────┘ └───────────┘
Key Components:

Frontend (Electron/React) — retro warroom UI, agent control panels, dashboards
Backend (Python FastAPI) — agent orchestration, trade execution, LLM coordination
Local LLM (Ollama) — runs on your machine, free, no API keys needed
Broker Integration — connects to Interactive Brokers, Kraken, Coinbase, etc.
Encrypted Vault — stores credentials locally, never transmitted
Context Engine — agents read your strategy files to make decisions


Execution Flow (How Trades Happen)
1. Agent wakes up (scheduled or real-time monitoring)
   ↓
2. Agent fetches market data from broker API
   ↓
3. Agent reads its context file (your trading rules)
   ↓
4. Agent sends market data + rules to local LLM: "Should we trade?"
   ↓
5. LLM reasons and generates recommendation + confidence score
   ↓
6. Based on execution mode:
   - AUTONOMOUS: Execute immediately (with position size limits)
   - HUMAN-IN-LOOP: Notify user, wait 5-30 seconds for veto
   - RISK-BASED: Execute if low-risk, wait for approval if high-risk
   ↓
7. If approved: Execute trade via broker API
   ↓
8. Log trade, update P&L, display in agent card on warroom floor

Who Should Use Labourious?
✅ Good Fit:

Retail investors who want to explore AI-driven strategies safely
Active traders looking to automate parts of their workflow
People who value privacy and want credentials on their machine
Traders interested in experimenting with multiple strategies simultaneously
Developers who want to extend/modify the system (it's open-source)

⚠️ Consider Carefully:

High-frequency traders (HFT) — latency may not be competitive
Traders with zero coding experience — setup still requires some technical steps
People unwilling to learn how to write trading rules (context files)
Those wanting cloud-based mobile trading apps (this is desktop-first)


Quick Start (30 Seconds)

Clone the repo:

bash   git clone https://github.com/yourusername/labourious.git
   cd labourious

Run the setup wizard:

bash   python setup.py
Follow prompts to:

Install dependencies
Set up Ollama (or choose cloud LLM)
Create encrypted vault for broker credentials
Run interactive tutorial


Launch the warroom:

bash   npm start  # Frontend
   python main.py  # Backend (separate terminal)

Open browser: http://localhost:3000
Connect your first broker, set capital allocation, and watch agents work.


Key Design Decisions & Rationale
Why Local Encryption Over Cloud Backup?

Security — keys never transmitted
Trust — auditable, open-source encryption
Simplicity — no account management, no 3rd-party dependency
Tradeoff — manual backups via encrypted export files (acceptable for trading software)

Why Ollama + Optional Cloud LLMs?

Accessibility — free tier works for most traders
Privacy — local reasoning by default, no market data sent to external APIs
Power users — can upgrade to Claude/GPT-4 for complex strategies
Cost-effective — agent decisions cost ~$0.001-0.01 with cloud LLMs

Why Autonomous + Human Modes?

Different strategies need different control — day trading can be fast, long-term should be deliberate
Risk management — allows users to set guardrails and still sleep
Learning — beginners can start in approval mode, graduate to autonomous as confidence grows

Why a Warroom Metaphor?

Engagement — monitoring trading is more fun when it feels like a strategy room
Intuition — agents as "players on a field" is instantly understandable
Extensibility — rooms naturally map to different strategies, custom rooms are obvious
Retro appeal — nostalgic 2D isometric view is distinctive, not another Bloomberg terminal clone


What's Included in This Repo?
labourious/
├── frontend/                    # Electron + React UI
│   ├── src/
│   │   ├── warroom/            # 2D isometric warroom component
│   │   ├── agent-inspector/    # Click agent → see details
│   │   ├── dashboards/         # P&L, performance, rule-tracing
│   │   └── settings/           # Config, broker setup, capital allocation
│   └── electron-main.js        # Desktop app entry point
│
├── backend/                     # Python FastAPI
│   ├── agents/                 # Agent logic & orchestration
│   ├── brokers/                # Broker API integrations (IB, Kraken, etc.)
│   ├── llm/                    # Local LLM + cloud LLM routing
│   ├── vault/                  # Encrypted credential storage
│   ├── context_engine/         # Context file parsing & rule matching
│   ├── trading/                # Trade execution, position tracking
│   └── api.py                  # FastAPI server
│
├── docs/                        # Comprehensive documentation
│   ├── SETUP.md                # Detailed installation guide
│   ├── ARCHITECTURE.md         # System design deep-dive
│   ├── AGENT_CREATION.md       # How to write trading rules
│   ├── CONTEXT_FILES.md        # Context file format & examples
│   ├── API_REFERENCE.md        # Backend API docs
│   ├── SECURITY.md             # Security model & best practices
│   ├── TROUBLESHOOTING.md      # Common issues & fixes
│   └── VIDEO_TUTORIALS.md      # Links to walkthrough videos
│
├── examples/                    # Pre-built agents & context files
│   ├── contexts/
│   │   ├── long_term_value.txt
│   │   ├── swing_momentum.txt
│   │   └── day_trade_signals.txt
│   └── agents/                 # Agent config templates
│
├── tests/                       # Unit & integration tests
├── docker/                      # Docker setup (alternative to native install)
├── .env.example                # Environment template
├── setup.py                    # Installation wizard
└── README.md                   # This file

Getting Started (Full Path)
Estimated time: 15-30 minutes for full setup

Installation Guide — three options (Python, Docker, Standalone)
Interactive Tutorial — runs on first launch
Agent Creation Guide — write your first trading rule
Context File Reference — syntax & examples
Broker Integration — connect your trading account securely
Your First Trade — paper trading walkthrough


Security Warnings ⚠️
Before you go live with real money:

Test in paper trading first — run agents against historical data, not real capital
Start small — begin with 1-5% of capital in automated mode
Understand your rules — review context files before deploying agents
Set position limits — enforce max position size, max drawdown, max leverage
Monitor regularly — check on agents daily initially (they won't run unattended forever)
Backup your keys — export encrypted keyfiles regularly
Keep Labourious updated — security patches released regularly

Autonomous execution disclaimer:

Labourious can execute trades 24/7 without human intervention
Market conditions can change rapidly; agents may face slippage, gaps, or liquidity issues
Past performance ≠ future results
Use at your own risk; you are responsible for all trades your agents make
Consider paper trading for weeks before going live


Roadmap
Phase 1 (MVP)

✅ Core agent orchestration
✅ 3 trading rooms (day, swing, long-term)
✅ Ollama integration
✅ Single broker integration (Interactive Brokers)
✅ Paper trading mode
✅ Basic UI warroom

Phase 2

Context file UI builder (non-coders can create rules)
Backtesting engine
More brokers (Kraken, Coinbase, Alpaca)
Multi-user support
Mobile companion app (iOS/Android)

Phase 3

Cloud LLM routing (Claude, GPT-4)
Advanced rule templates (ML-based signals, sentiment analysis)
Collaborative agent sharing (GitHub-based rule library)
Advanced portfolio analytics


Contributing
Labourious is open-source and welcomes contributions!

Bug fixes — submit a PR
New brokers — add to backend/brokers/
Trading rules — contribute context file examples
UI improvements — enhance the warroom interface
Documentation — help translate or improve guides

See CONTRIBUTING.md for details.

License
MIT License — use Labourious for personal or commercial projects, modify freely.

Community & Support

GitHub Issues — bug reports & feature requests
Discussions — ask questions, share strategies
Discord (TBD) — real-time chat with other users
Email — hello@labourious.dev


Disclaimer
Labourious is a tool, not financial advice. Trading involves risk. Past performance does not guarantee future results. The creator and contributors are not responsible for losses incurred through use of this software. Use at your own risk and never risk money you cannot afford to lose.

The Vision
Labourious exists because institutional traders have teams of quants, APIs, and rooms full of screens. Retail traders shouldn't have to choose between:

Expensive platforms (Bloomberg, proprietary systems)
Cloud-dependent software (security concerns)
Oversimplified robo-advisors (no control)

With Labourious, you get the tools. You keep the control. You own the system. Welcome to your AI trading warroom.

Ready to get started? Go to Installation Guide →
