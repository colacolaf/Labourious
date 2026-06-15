Labourious Architecture & Technical Design
For developers and technically curious users who want to understand how Labourious works under the hood.

System Overview
┌─────────────────────────────────────────────────────────────────┐
│                    USER (Warroom Interface)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                   HTTP (REST/WebSocket)
                         │
┌────────────────────────▼────────────────────────────────────────┐
│              Frontend (Electron + React)                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ - Warroom Renderer (2D isometric view)                  │   │
│  │ - Agent Inspector (click to drill-down)                 │   │
│  │ - Dashboard (P&L, metrics, trades)                      │   │
│  │ - Settings (broker config, allocation)                  │   │
│  └─────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                   HTTP/WS to :8000
                         │
┌────────────────────────▼────────────────────────────────────────┐
│           Backend (Python FastAPI)                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Agent Orchestrator (manages agent lifecycle)            │   │
│  │  ├─ Agent Scheduler (runs agents on schedule)          │   │
│  │  ├─ Agent Executor (makes trade decisions)             │   │
│  │  ├─ Trade Executor (sends orders to brokers)           │   │
│  │  └─ Agent Monitor (tracks performance)                 │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LLM Router (local/cloud orchestration)                  │   │
│  │  ├─ Local LLM Adapter (Ollama integration)             │   │
│  │  ├─ Cloud LLM Adapter (Claude/GPT API)                 │   │
│  │  └─ Prompt Engineer (context → trading prompt)          │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Broker Integration Layer                                │   │
│  │  ├─ Interactive Brokers Connector                      │   │
│  │  ├─ Kraken Connector                                   │   │
│  │  ├─ Coinbase Connector                                 │   │
│  │  └─ (Pluggable for new brokers)                        │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Data Layer                                              │   │
│  │  ├─ SQLite DB (trades, agents, logs)                   │   │
│  │  ├─ Encrypted Vault (API keys)                         │   │
│  │  ├─ Cache (market data, indicators)                    │   │
│  │  └─ File System (context files, configs)               │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────┬────────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
        ▼                ▼                ▼
    ┌────────┐      ┌────────┐      ┌──────────┐
    │ Broker │      │ Ollama │      │ Local DB │
    │ APIs   │      │ (LLM)  │      │ + Vault  │
    └────────┘      └────────┘      └──────────┘

Component Deep-Dive
1. Frontend (Electron + React)
Location: frontend/
Key Components:
Warroom Renderer
javascript// frontend/src/warroom/WarroomRenderer.jsx
- Renders 2D isometric canvas
- Positions agents as interactive sprites
- Real-time animation of agent activity
- Drag-to-pan, scroll-to-zoom controls
- Performance: uses WebGL for 50+ agents
Data flow:

Frontend polls backend /api/agents/status every 2 seconds
Each agent has {position, state, p_and_l, trades_today}
Frontend animates agent state changes
User clicks agent → opens Inspector panel

Agent Inspector
javascript// frontend/src/inspector/AgentInspector.jsx
- Modal showing agent details when clicked
- Tabs: Overview, Trades, Rules, Performance, Settings
- Real-time trade notifications
- Approve/reject trade buttons (for human-in-loop mode)
Data flow:

User clicks agent
Frontend fetches /api/agents/{agent_id}/details
Returns: recent trades, rule firing history, performance metrics
User approves trade → POST to /api/agents/{agent_id}/approve

Dashboard
javascript// frontend/src/dashboard/Dashboard.jsx
- Portfolio overview (total P&L, allocation)
- Agent leaderboard (by return, Sharpe, win rate)
- Trade history (filterable, exportable)
- Performance charts (daily equity curve, drawdown)
Settings
javascript// frontend/src/settings/Settings.jsx
- Broker connection management
- LLM selection (local/cloud)
- Capital allocation sliders
- Agent enable/disable toggles
- Paper trading / Live mode switch
2. Backend (Python FastAPI)
Location: backend/
Agent Orchestrator
python# backend/orchestrator.py

class AgentOrchestrator:
    def __init__(self):
        self.agents = {}  # {agent_id: AgentInstance}
        self.scheduler = APScheduler()  # Task scheduler
        self.llm_router = LLMRouter()
        self.trade_executor = TradeExecutor()
        
    async def run_agent_loop(self, agent_id):
        """Main agent execution loop"""
        agent = self.agents[agent_id]
        
        # 1. Fetch market data
        market_data = await self.fetch_market_data(agent.asset)
        
        # 2. Read agent's context file
        context = agent.load_context_file()
        
        # 3. Ask LLM for decision
        decision = await self.llm_router.decide(
            market_data=market_data,
            context=context,
            agent_config=agent.config
        )
        
        # 4. Execute trade (or get approval)
        if agent.execution_mode == "autonomous":
            await self.trade_executor.execute(decision)
        elif agent.execution_mode == "human_in_loop":
            self.notify_user(decision)  # Wait for approval
        
        # 5. Log results
        await self.log_trade(agent_id, decision, execution_result)
Agent Scheduling:

Each agent has a check_frequency (e.g., every 5 minutes)
APScheduler runs agents on a concurrent thread pool
For day traders: every 5-60 seconds
For swing traders: once per day
For long-term: once per week

LLM Router
python# backend/llm/router.py

class LLMRouter:
    async def decide(self, market_data, context, agent_config):
        """Route reasoning through local or cloud LLM"""
        
        # Build prompt from context file + market data
        prompt = self.build_prompt(market_data, context)
        
        if agent_config.use_local_llm:
            # Use Ollama (offline, free)
            response = await self.call_ollama(prompt)
        else:
            # Use Claude API (better reasoning, cost $$)
            response = await self.call_claude(prompt)
        
        # Parse response into structured decision
        decision = self.parse_decision(response)
        # {
        #   "action": "buy" | "sell" | "hold",
        #   "confidence": 0.85,
        #   "reason": "RSI < 30 AND price below MA20",
        #   "position_size": 0.05,  # 5% of capital
        #   "stop_loss": -0.05,
        #   "take_profit": 0.15
        # }
        
        return decision
    
    async def call_ollama(self, prompt: str):
        """Call local Ollama instance"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt}
            )
        return response.json()["response"]
    
    async def call_claude(self, prompt: str):
        """Call Claude API (requires API key in vault)"""
        api_key = self.vault.get("ANTHROPIC_API_KEY")
        response = await anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text
Prompt Engineering:
pythondef build_prompt(market_data, context):
    return f"""
You are a trading AI. Based on the rules below and market data,
decide whether to BUY, SELL, or HOLD.

TRADING RULES:
{context}

CURRENT MARKET DATA:
- Price: ${market_data.price}
- RSI(14): {market_data.rsi}
- Volume: {market_data.volume}
- 20-day MA: ${market_data.ma20}

Respond ONLY with valid JSON:
{{
  "action": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}
"""
Trade Executor
python# backend/trading/executor.py

class TradeExecutor:
    async def execute(self, decision, agent_config):
        """Execute trade via broker API"""
        
        # 1. Validate decision
        if decision.confidence < 0.5:
            return {"status": "rejected", "reason": "low_confidence"}
        
        # 2. Size position
        position_size = self.calculate_position_size(
            agent_config.capital_allocation,
            decision.position_size,
            agent_config.max_position_size
        )
        
        # 3. Get broker connector
        broker = self.get_broker(agent_config.broker)
        
        # 4. Submit order
        order = await broker.place_order(
            symbol=agent_config.asset,
            side=decision.action,
            quantity=position_size,
            order_type="market"
        )
        
        # 5. Set stops
        if decision.stop_loss:
            await broker.set_stop_loss(order.id, decision.stop_loss)
        if decision.take_profit:
            await broker.set_take_profit(order.id, decision.take_profit)
        
        # 6. Log trade
        await self.db.log_trade({
            "agent_id": agent_config.id,
            "order_id": order.id,
            "decision": decision,
            "timestamp": datetime.now(),
            "status": "executed"
        })
        
        return {"status": "success", "order": order}
Broker Integrations
Interactive Brokers:
python# backend/brokers/interactive_brokers.py

class IBConnector:
    def __init__(self, account_id, api_key):
        self.ib = IB()
        self.ib.connect('127.0.0.1', 7497)  # localhost, port 7497
    
    async def get_account_balance(self):
        """Fetch account balance"""
        return self.ib.accountSummary()[0].value
    
    async def place_order(self, symbol, side, quantity):
        """Place market order"""
        contract = Stock(symbol, 'SMART', 'USD')
        order = MarketOrder(side, quantity)
        trade = self.ib.placeOrder(contract, order)
        return trade
Kraken:
python# backend/brokers/kraken.py

class KrakenConnector:
    def __init__(self, api_key, private_key):
        self.client = krakenex.API(api_key, private_key)
    
    async def get_account_balance(self):
        return self.client.query_private('Balance')
    
    async def place_order(self, symbol, side, quantity):
        return self.client.query_private('AddOrder', {
            'pair': symbol,
            'type': side,
            'ordertype': 'market',
            'volume': quantity
        })
3. Data Layer
Encrypted Vault
python# backend/vault/encrypted_vault.py

from cryptography.fernet import Fernet

class EncryptedVault:
    def __init__(self, vault_password: str):
        # Derive key from password using PBKDF2
        self.key = PBKDF2(vault_password, salt=..., iterations=100000)
        self.cipher = Fernet(self.key)
    
    def store(self, key: str, value: str):
        """Encrypt and store credential"""
        encrypted = self.cipher.encrypt(value.encode())
        db.store(key, encrypted)
    
    def retrieve(self, key: str):
        """Decrypt and retrieve credential"""
        encrypted = db.retrieve(key)
        return self.cipher.decrypt(encrypted).decode()
Vault contents (encrypted at rest):

Broker API keys
API secrets
Private keys (crypto)

SQLite Database Schema
sql-- Agents
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT,
    room TEXT,  -- day_trading, swing_trading, long_term
    asset TEXT,
    config JSON,
    enabled BOOLEAN,
    created_at TIMESTAMP
);

-- Trades
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    agent_id TEXT REFERENCES agents(id),
    symbol TEXT,
    side TEXT,  -- BUY or SELL
    quantity REAL,
    entry_price REAL,
    entry_time TIMESTAMP,
    exit_price REAL,
    exit_time TIMESTAMP,
    p_and_l REAL,
    reason TEXT,
    status TEXT  -- open, closed, rejected
);

-- Agent Performance (aggregate)
CREATE TABLE agent_performance (
    agent_id TEXT REFERENCES agents(id),
    date DATE,
    total_return_pct REAL,
    win_rate REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    num_trades INT
);

-- Logs
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP,
    agent_id TEXT,
    level TEXT,  -- INFO, WARNING, ERROR
    message TEXT
);

Data Flow: Example Trade Execution
Scenario: Day trader wakes up at 9:30am, agent checks Bitcoin
1. SCHEDULER TRIGGERS
   └─ "BTC Day Trader" agent's 5-min check fires
   
2. MARKET DATA FETCH
   ├─ Fetch BTC/USD price from Kraken
   ├─ Fetch volume, RSI(14), MACD, moving averages
   └─ Store in cache for 1 minute (avoid API spam)
   
3. CONTEXT READING
   ├─ Load contexts/btc_momentum.txt
   ├─ Parse rules: "Buy if price > MA20 AND RSI < 70"
   └─ Prepare for LLM reasoning
   
4. LLM DECISION
   ├─ Build prompt: rules + market data
   ├─ Send to Ollama (local) or Claude API
   └─ Response: {"action": "buy", "confidence": 0.82, ...}
   
5. APPROVAL GATE
   ├─ If mode = "autonomous" → skip to execution
   ├─ If mode = "human_in_loop" → notify user
   │  └─ WebSocket message to frontend
   │  └─ Wait 30 seconds for user approval
   │  └─ If no response → reject (safe default)
   └─ If mode = "risk_based" → auto-execute if low risk
   
6. TRADE EXECUTION
   ├─ Size position: $2,000 (from config)
   ├─ Get Kraken connector from broker manager
   ├─ Place market order: BUY 0.05 BTC
   └─ Set stops: SL -5%, TP +15%
   
7. LOGGING & NOTIFICATIONS
   ├─ Write trade to DB
   ├─ Update agent P&L
   ├─ Notify user via WebSocket
   └─ Broadcast to warroom UI (agent card updates)
   
8. CONTINUOUS MONITORING
   ├─ Check position every 10 seconds
   ├─ If stop loss or take profit hit → close automatically
   ├─ Update UI with live P&L
   └─ Log exit trade and performance

Security Architecture
Credential Storage
User's Machine:
┌─────────────────────────────────────────┐
│  ~/.labourious/                         │
│  ├─ vault.db (encrypted at rest)        │
│  │  └─ Encrypted with AES-256 + PBKDF2 │
│  ├─ vault.key (master key)              │
│  │  └─ Derived from user's password     │
│  └─ keys/backup.enc                     │
│     └─ User-controlled backup           │
└─────────────────────────────────────────┘

Broker Side:
┌─────────────────────────────────────────┐
│  Broker API (Kraken, IB, etc.)          │
│  ├─ Never receives vault password       │
│  ├─ Only receives API keys              │
│  │  (which are already broker-facing)   │
│  └─ HTTPS encryption in transit         │
└─────────────────────────────────────────┘
No Cloud Sync of Keys

Keys stay LOCAL only
Encrypted backup is user-controlled
If system compromised, attacker gets encrypted blob (useless without password)

API Key Best Practices
✅ Create broker API keys with LIMITED permissions:
   - For backtesting: Read-only (no trade execution)
   - For paper trading: Trade permissions, paper account only
   - For live trading: Trade permissions, live account, rate limits

✅ Regular rotation:
   - Generate new API key every 6 months
   - Delete old key from broker
   - Update in Labourious vault

✅ Never log keys:
   - Vault passwords never written to logs
   - API keys masked in error messages
   - Transactions logged (not credentials)

Performance Optimization
Caching Strategy
python# Market data cache (1 minute TTL)
CACHE = {
    "BTC/USD": {
        "price": 45230.50,
        "rsi": 62.3,
        "volume": 2850000,
        "fetched_at": 1718042400
    }
}

# Only fetch if > 1 minute old
if time.time() - CACHE["BTC/USD"]["fetched_at"] > 60:
    refresh_market_data()
Concurrent Agent Execution
python# Use thread pool for parallel agent loops
executor = ThreadPoolExecutor(max_workers=10)

for agent_id, agent in orchestrator.agents.items():
    executor.submit(run_agent_loop, agent_id)
    # Each agent runs independently
WebSocket for Live Updates
python# Instead of polling every 2 seconds,
# use WebSocket for push updates:
# - Agent trade → immediately push to frontend
# - P&L change → immediately push to frontend
# - Status change → immediately push to frontend

# Reduces load by 80% vs polling

Extensibility: Adding a New Broker
To add support for a new broker (e.g., Alpaca):

Create new connector:

python# backend/brokers/alpaca.py

class AlpacaConnector(BrokerConnector):
    def __init__(self, api_key, secret):
        self.client = StockMarketDataClient(api_key)
    
    async def get_account_balance(self):
        return self.client.get_account().equity
    
    async def place_order(self, symbol, side, quantity):
        return self.client.submit_order(
            OrderData(symbol=symbol, qty=quantity, side=side, order_type="market")
        )

Register in broker manager:

python# backend/brokers/manager.py

BROKERS = {
    "interactive_brokers": IBConnector,
    "kraken": KrakenConnector,
    "coinbase": CoinbaseConnector,
    "alpaca": AlpacaConnector,  # ← Add here
}

Test integration:

bashpytest backend/tests/test_alpaca_connector.py

Testing Strategy
Unit Tests
python# Test individual components
- LLM prompt generation
- Position sizing
- Order validation
- Trade logging
Integration Tests
python# Test component interactions
- Agent execution loop
- Broker API calls (mock)
- Trade logging to DB
Paper Trading Tests
python# Test full system with simulated trades
- Run agent on historical data
- Verify P&L calculations
- Check order execution correctness

Monitoring & Observability
Logging
python# backend/logging.py

import logging

logger = logging.getLogger("labourious")
logger.info(f"Agent {agent_id} executing trade: {decision}")
logger.error(f"Broker connection failed: {error}")
Metrics
python# Prometheus metrics exposed at /metrics
- agents_active (counter)
- trades_executed_total (counter)
- trade_decision_latency_ms (histogram)
- llm_response_time_ms (histogram)
Alerts
python# Alert if:
- Agent P&L drops > 25%
- Trade execution fails
- LLM response timeout
- Broker connection lost

Deployment Topology
Single Machine (Default)
┌─────────────────────────────────┐
│       User's Computer           │
│                                 │
│  ├─ Frontend (port 3000)        │
│  ├─ Backend (port 8000)         │
│  ├─ SQLite DB (local file)      │
│  ├─ Ollama (port 11434)         │
│  └─ Vault (encrypted file)      │
└─────────────────────────────────┘
Docker Container
┌─────────────────────────────────┐
│   Docker Container              │
│                                 │
│  ├─ Frontend (port 3000)        │
│  ├─ Backend (port 8000)         │
│  ├─ SQLite DB (volume mount)    │
│  ├─ Ollama (volume mount)       │
│  └─ Vault (volume mount)        │
└─────────────────────────────────┘
    ↓ (credentials stay on host machine)
┌─────────────────────────────────┐
│   Host Machine                  │
│  ~/.labourious/vault.db (encrypted)
└─────────────────────────────────┘

Future Scalability
For users who want to run 100+ agents:

Load balancing — run multiple backend instances
Message queue — use Redis/Kafka for agent job scheduling
Distributed LLM — horizontal scaling of LLM inference
Time-series DB — use InfluxDB instead of SQLite for high-frequency trades

(Out of scope for MVP)

Conclusion
Labourious is built on proven, simple architecture:

Frontend (Electron) = user interface
Backend (FastAPI) = business logic
LLM (Ollama/Claude) = decision making
Brokers = trade execution
Database (SQLite) = audit trail

Each component is isolated, testable, and extensible.
Next Steps:

Read AGENT_CREATION.md to understand context files
Review code in backend/agents/ to see executor logic
Run tests: pytest to verify system health
