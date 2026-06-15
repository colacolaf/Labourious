Labourious: Complete Project Structure
This document shows the exact folder/file organization and what to implement in each.

Repository Root Structure
labourious/
├── README.md                          # Main project overview (already written)
├── CONTRIBUTING.md                    # How to contribute to the project
├── LICENSE                            # MIT License
├── .gitignore                         # Git ignore patterns
├── .env.example                       # Environment variable template
│
├── frontend/                          # React + Electron frontend
│   ├── package.json
│   ├── webpack.config.js
│   ├── public/
│   │   ├── index.html
│   │   └── assets/
│   │       ├── fonts/
│   │       ├── icons/
│   │       └── sounds/
│   ├── src/
│   │   ├── index.jsx
│   │   ├── App.jsx
│   │   ├── electron-main.js           # Electron entry point
│   │   ├── preload.js                 # IPC bridge
│   │   │
│   │   ├── components/
│   │   │   ├── Warroom/               # Main warroom interface
│   │   │   │   ├── Warroom.jsx        # 2D isometric renderer
│   │   │   │   ├── warroom.css
│   │   │   │   ├── AgentCard.jsx      # Visual representation of agent
│   │   │   │   └── utils/
│   │   │   │       ├── isometric.js
│   │   │   │       └── pathfinding.js
│   │   │   │
│   │   │   ├── AgentInspector/        # Drill-down panel
│   │   │   │   ├── AgentInspector.jsx
│   │   │   │   ├── Tabs/
│   │   │   │   │   ├── Overview.jsx
│   │   │   │   │   ├── Trades.jsx
│   │   │   │   │   ├── Rules.jsx
│   │   │   │   │   ├── Performance.jsx
│   │   │   │   │   └── Settings.jsx
│   │   │   │   └── inspector.css
│   │   │   │
│   │   │   ├── Dashboard/
│   │   │   │   ├── Dashboard.jsx
│   │   │   │   ├── PortfolioSummary.jsx
│   │   │   │   ├── AgentLeaderboard.jsx
│   │   │   │   ├── TradeHistory.jsx
│   │   │   │   ├── Charts/
│   │   │   │   │   ├── EquityCurve.jsx
│   │   │   │   │   ├── DrawdownChart.jsx
│   │   │   │   │   └── AllocationPie.jsx
│   │   │   │   └── dashboard.css
│   │   │   │
│   │   │   ├── Settings/
│   │   │   │   ├── Settings.jsx
│   │   │   │   ├── BrokerSetup.jsx
│   │   │   │   ├── LLMConfig.jsx
│   │   │   │   ├── CapitalAllocation.jsx
│   │   │   │   ├── AgentBuilder.jsx
│   │   │   │   └── settings.css
│   │   │   │
│   │   │   ├── Tutorial/
│   │   │   │   ├── TutorialWizard.jsx
│   │   │   │   ├── steps/
│   │   │   │   │   ├── Step1Welcome.jsx
│   │   │   │   │   ├── Step2Broker.jsx
│   │   │   │   │   ├── Step3LLM.jsx
│   │   │   │   │   ├── Step4Allocation.jsx
│   │   │   │   │   └── Step5Ready.jsx
│   │   │   │   └── tutorial.css
│   │   │   │
│   │   │   └── Common/
│   │   │       ├── Header.jsx
│   │   │       ├── Sidebar.jsx
│   │   │       ├── Notification.jsx
│   │   │       ├── Modal.jsx
│   │   │       └── common.css
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.js
│   │   │   ├── useAgent.js
│   │   │   ├── useAPI.js
│   │   │   └── useWarroomState.js
│   │   │
│   │   ├── utils/
│   │   │   ├── api-client.js           # HTTP client for backend
│   │   │   ├── ws-client.js            # WebSocket client
│   │   │   ├── formatting.js           # Number/date formatting
│   │   │   ├── validators.js
│   │   │   └── constants.js
│   │   │
│   │   ├── styles/
│   │   │   ├── index.css
│   │   │   ├── retro-theme.css         # Retro color scheme
│   │   │   ├── dark-mode.css
│   │   │   └── animations.css
│   │   │
│   │   └── store/
│   │       ├── store.js                # Redux or Zustand
│   │       ├── slices/
│   │       │   ├── agents.js
│   │       │   ├── warroom.js
│   │       │   ├── trades.js
│   │       │   └── settings.js
│   │       └── middleware/
│   │           └── api.js
│   │
│   └── tests/
│       ├── __mocks__/
│       ├── components/
│       ├── hooks/
│       └── utils/
│
├── backend/                           # Python FastAPI backend
│   ├── requirements.txt
│   ├── main.py                        # FastAPI app entry
│   ├── config.py                      # Configuration management
│   │
│   ├── api/                           # REST API routes
│   │   ├── __init__.py
│   │   ├── agents.py                  # GET/POST agents
│   │   ├── brokers.py                 # Broker setup endpoints
│   │   ├── trades.py                  # Trade history, stats
│   │   ├── dashboard.py               # Portfolio data
│   │   ├── settings.py                # Config endpoints
│   │   ├── health.py                  # Health check
│   │   └── websocket.py               # WebSocket connections
│   │
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── agent_orchestrator.py      # Main orchestration logic
│   │   ├── scheduler.py               # APScheduler integration
│   │   ├── agent_executor.py          # Agent execution logic
│   │   └── monitor.py                 # Agent monitoring
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent.py                   # Agent class definition
│   │   ├── context_parser.py          # Parse context files
│   │   ├── room.py                    # Room management
│   │   └── templates/
│   │       ├── day_trader.py
│   │       ├── swing_trader.py
│   │       └── long_term_investor.py
│   │
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_router.py              # Local/Cloud routing
│   │   ├── ollama_client.py           # Ollama integration
│   │   ├── claude_client.py           # Claude API integration
│   │   ├── gpt_client.py              # GPT API integration
│   │   ├── prompt_engineer.py         # Prompt building
│   │   └── decision_parser.py         # Parse LLM responses
│   │
│   ├── brokers/
│   │   ├── __init__.py
│   │   ├── base_broker.py             # Abstract base class
│   │   ├── broker_manager.py          # Broker registry & routing
│   │   ├── interactive_brokers.py     # IB integration
│   │   ├── kraken.py                  # Kraken integration
│   │   ├── coinbase.py                # Coinbase integration
│   │   ├── alpaca.py                  # Alpaca integration (future)
│   │   └── market_data.py             # Market data fetching
│   │
│   ├── trading/
│   │   ├── __init__.py
│   │   ├── trade_executor.py          # Order execution
│   │   ├── position_manager.py        # Track open positions
│   │   ├── risk_manager.py            # Position size, stop loss
│   │   └── logger.py                  # Trade logging
│   │
│   ├── vault/
│   │   ├── __init__.py
│   │   ├── encrypted_vault.py         # Encryption/decryption
│   │   ├── vault_manager.py           # Vault operations
│   │   └── key_derivation.py          # PBKDF2 key derivation
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py                      # SQLite connection
│   │   ├── models.py                  # SQLAlchemy models
│   │   ├── migrations/
│   │   │   ├── init.sql               # Schema creation
│   │   │   └── add_...sql             # Future migrations
│   │   └── queries.py                 # Common queries
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent.py                   # Agent schema
│   │   ├── trade.py                   # Trade schema
│   │   ├── performance.py             # Performance metrics
│   │   └── broker_config.py           # Broker credentials
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py                  # Logging setup
│   │   ├── decorators.py              # Useful decorators
│   │   ├── validators.py              # Input validation
│   │   └── helpers.py                 # General utilities
│   │
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py                    # Authentication
│   │   ├── error_handler.py           # Global error handling
│   │   └── rate_limiter.py            # Rate limiting
│   │
│   └── tests/
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_agents.py
│       ├── test_brokers.py
│       ├── test_llm.py
│       ├── test_trading.py
│       └── fixtures/
│           ├── mock_market_data.py
│           └── mock_broker.py
│
├── docs/                              # Comprehensive documentation
│   ├── SETUP.md                       # Installation guide (already written)
│   ├── AGENT_CREATION.md              # Agent writing guide (already written)
│   ├── CONTEXT_FILES.md               # Context file reference
│   ├── ARCHITECTURE.md                # Technical design (already written)
│   ├── API_REFERENCE.md               # Backend API docs
│   ├── BROKERS.md                     # Broker-specific setup
│   ├── SECURITY.md                    # Security model & best practices
│   ├── TROUBLESHOOTING.md             # Common issues & fixes
│   ├── CONTRIBUTING.md                # Developer guide
│   ├── FAQ.md                         # Frequently asked questions
│   └── VIDEO_TUTORIALS.md             # Links to YouTube tutorials
│
├── examples/                          # Example agents & configs
│   ├── contexts/
│   │   ├── long_term_value.txt        # Example value investing rules
│   │   ├── swing_momentum.txt         # Example swing trading rules
│   │   ├── day_trade_signals.txt      # Example day trading rules
│   │   └── README.md                  # How to use examples
│   │
│   ├── agents/
│   │   ├── sp500_value_investor.json
│   │   ├── btc_momentum_trader.json
│   │   ├── tech_swing_trader.json
│   │   └── README.md                  # Agent template guide
│   │
│   └── portfolios/
│       ├── conservative.json          # 80/15/5 allocation
│       ├── moderate.json              # 60/30/10 allocation
│       └── aggressive.json            # 40/40/20 allocation
│
├── docker/
│   ├── Dockerfile                     # Multi-stage build
│   ├── docker-compose.yml             # Compose config
│   ├── entrypoint.sh                  # Startup script
│   └── README.md                      # Docker setup guide
│
├── scripts/
│   ├── setup.py                       # Interactive setup wizard
│   ├── verify_install.py              # Installation verification
│   ├── manage_vault.py                # Vault management CLI
│   ├── export_trades.py               # Export trade data
│   ├── backtest.py                    # Backtesting CLI
│   └── migrate_db.py                  # Database migrations
│
├── tests/
│   ├── integration/
│   │   ├── test_full_flow.py          # End-to-end tests
│   │   └── test_broker_integration.py
│   ├── e2e/
│   │   └── test_warroom_ui.py         # Selenium/Playwright tests
│   └── performance/
│       └── test_agent_latency.py      # Load testing
│
├── .github/
│   ├── workflows/
│   │   ├── tests.yml                  # CI/CD pipeline
│   │   ├── security.yml               # Security checks
│   │   └── release.yml                # Release automation
│   └── ISSUE_TEMPLATE.md
│
├── .dockerignore
├── .gitattributes
└── setup.cfg                          # Python config

File Implementation Guide
Frontend Key Files
frontend/src/electron-main.js
javascript// Electron app entry point
// - Creates main window
// - Handles IPC from renderer
// - Manages app lifecycle

const { app, BrowserWindow, ipcMain } = require('electron');

function createWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js')
    }
  });
  
  if (process.env.NODE_ENV === 'development') {
    win.loadURL('http://localhost:3000');
    win.webDevTools.openDevTools();
  } else {
    win.loadFile(path.join(__dirname, '../build/index.html'));
  }
}

app.on('ready', createWindow);
frontend/src/components/Warroom/Warroom.jsx
javascript// 2D isometric warroom renderer
// - Renders agent cards on 2D grid
// - Handles user interactions (click agent, drag camera)
// - Real-time state updates via WebSocket

import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../../hooks/useWebSocket';
import AgentCard from './AgentCard';

export default function Warroom() {
  const [agents, setAgents] = useState([]);
  const ws = useWebSocket();
  
  useEffect(() => {
    // Listen for agent updates
    ws.on('agent_update', (agent) => {
      setAgents(agents => agents.map(a => 
        a.id === agent.id ? agent : a
      ));
    });
  }, []);
  
  return (
    <div className="warroom">
      <canvas id="warroom-canvas" width="1400" height="900"></canvas>
      {agents.map(agent => (
        <AgentCard 
          key={agent.id} 
          agent={agent}
          onOpen={() => openInspector(agent.id)}
        />
      ))}
    </div>
  );
}
frontend/src/components/AgentInspector/AgentInspector.jsx
javascript// Right-side panel showing agent details
// - Tabs: Overview, Trades, Rules, Performance, Settings
// - Approve/reject button for human-in-loop mode
// - Live P&L updates

export default function AgentInspector({ agentId }) {
  const [agent, setAgent] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  
  useEffect(() => {
    fetchAgentDetails(agentId).then(setAgent);
  }, [agentId]);
  
  const handleApproveTrade = async (tradeId) => {
    await api.post(`/agents/${agentId}/approve`, { trade_id: tradeId });
  };
  
  return (
    <div className="inspector">
      <div className="inspector-tabs">
        <button onClick={() => setActiveTab('overview')}>Overview</button>
        <button onClick={() => setActiveTab('trades')}>Trades</button>
        <button onClick={() => setActiveTab('rules')}>Rules</button>
        <button onClick={() => setActiveTab('performance')}>Performance</button>
        <button onClick={() => setActiveTab('settings')}>Settings</button>
      </div>
      
      <div className="inspector-content">
        {activeTab === 'overview' && <Overview agent={agent} />}
        {activeTab === 'trades' && <Trades agent={agent} onApprove={handleApproveTrade} />}
        {/* ... other tabs ... */}
      </div>
    </div>
  );
}
Backend Key Files
backend/main.py
python# FastAPI application entry point
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="Labourious Trading API")

# Add CORS middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"])

# Import routes
from api import agents, brokers, trades, dashboard, settings, health

app.include_router(agents.router)
app.include_router(brokers.router)
app.include_router(trades.router)
app.include_router(dashboard.router)
app.include_router(settings.router)
app.include_router(health.router)

# Initialize components
from orchestrator import AgentOrchestrator
from vault import EncryptedVault

vault = EncryptedVault(os.getenv('VAULT_PASSWORD'))
orchestrator = AgentOrchestrator(vault)

@app.on_event("startup")
async def startup():
    await orchestrator.initialize()

@app.on_event("shutdown")
async def shutdown():
    await orchestrator.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
backend/orchestrator/agent_orchestrator.py
python# Main orchestration logic
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

class AgentOrchestrator:
    def __init__(self, vault):
        self.agents = {}
        self.vault = vault
        self.scheduler = AsyncIOScheduler()
        self.trade_executor = TradeExecutor(vault)
        self.llm_router = LLMRouter()
        
    async def initialize(self):
        """Load agents from DB and start scheduler"""
        self.agents = await self.load_agents_from_db()
        
        for agent in self.agents.values():
            self.scheduler.add_job(
                self.run_agent,
                'interval',
                seconds=agent.config.check_frequency,
                args=[agent.id]
            )
        
        self.scheduler.start()
    
    async def run_agent(self, agent_id):
        """Execute single agent"""
        agent = self.agents[agent_id]
        
        if not agent.enabled:
            return
        
        try:
            # Fetch market data
            market_data = await self.fetch_market_data(agent.asset)
            
            # Read context file
            context = agent.load_context()
            
            # Get LLM decision
            decision = await self.llm_router.decide(
                market_data=market_data,
                context=context,
                agent=agent
            )
            
            # Execute or wait for approval
            await self.execute_decision(agent, decision)
            
        except Exception as e:
            logger.error(f"Agent {agent_id} error: {e}")
backend/llm/llm_router.py
python# LLM decision routing (local or cloud)

class LLMRouter:
    async def decide(self, market_data, context, agent):
        """Route to local or cloud LLM"""
        
        prompt = self.build_prompt(market_data, context)
        
        if agent.config.use_local_llm:
            response = await self.call_ollama(prompt)
        else:
            response = await self.call_claude(prompt)
        
        decision = self.parse_decision(response)
        return decision
    
    def build_prompt(self, market_data, context):
        return f"""
You are a trading AI. Based on the rules and current market data,
decide to BUY, SELL, or HOLD.

TRADING RULES:
{context}

CURRENT MARKET DATA:
Price: ${market_data['price']}
RSI: {market_data['rsi']}
Volume: {market_data['volume']}

Respond ONLY with JSON:
{{
  "action": "buy|sell|hold",
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}
"""
    
    async def call_ollama(self, prompt):
        """Call local Ollama instance"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "mistral", "prompt": prompt}
            )
        return response.json()["response"]
    
    async def call_claude(self, prompt):
        """Call Claude API"""
        import anthropic
        client = anthropic.AsyncAnthropic()
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text

Database Schema
sql-- agents table
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    room TEXT NOT NULL,  -- day_trading, swing_trading, long_term
    asset TEXT NOT NULL,
    broker TEXT,
    enabled BOOLEAN DEFAULT TRUE,
    config JSON NOT NULL,  -- execution_mode, position_size, etc.
    context_file_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- trades table
CREATE TABLE trades (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,  -- BUY, SELL
    quantity REAL NOT NULL,
    entry_price REAL NOT NULL,
    entry_time TIMESTAMP NOT NULL,
    exit_price REAL,
    exit_time TIMESTAMP,
    p_and_l REAL,
    p_and_l_percent REAL,
    reason TEXT,
    status TEXT,  -- open, closed, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- agent_performance (daily aggregate)
CREATE TABLE agent_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id TEXT NOT NULL REFERENCES agents(id),
    date DATE NOT NULL,
    total_return_pct REAL,
    win_rate REAL,
    sharpe_ratio REAL,
    max_drawdown REAL,
    num_trades INTEGER,
    num_wins INTEGER,
    num_losses INTEGER
);

-- logs
CREATE TABLE logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_id TEXT,
    level TEXT,  -- INFO, WARNING, ERROR, DEBUG
    message TEXT,
    context JSON
);

API Endpoint Structure
GET  /api/health                          # Health check
GET  /api/agents                          # List all agents
POST /api/agents                          # Create agent
GET  /api/agents/{id}                     # Get agent details
POST /api/agents/{id}/approve             # Approve trade (human-in-loop)
POST /api/agents/{id}/toggle              # Enable/disable agent
POST /api/agents/{id}/update-context      # Update context file

POST /api/brokers/connect                 # Setup new broker
GET  /api/brokers/status                  # Check broker connection
GET  /api/brokers/{broker}/accounts       # List accounts

GET  /api/trades                          # Trade history
GET  /api/trades/{id}                     # Trade details
POST /api/trades/export                   # Export as CSV

GET  /api/dashboard/summary               # Portfolio summary
GET  /api/dashboard/performance           # Agent performance
GET  /api/dashboard/allocation            # Capital allocation

POST /api/settings/allocation             # Update allocation
POST /api/settings/llm                    # Configure LLM
POST /api/settings/vault-password         # Change vault password

Dependencies
Frontend (frontend/package.json)
json{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.4.0",
    "zustand": "^4.3.0",
    "recharts": "^2.7.0",
    "date-fns": "^2.30.0"
  },
  "devDependencies": {
    "electron": "^latest",
    "webpack": "^5",
    "@babel/core": "^7.22.0"
  }
}
Backend (backend/requirements.txt)
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
aiosqlite==3.14.0
httpx==0.25.1
cryptography==41.0.5
apscheduler==3.10.4
pydantic==2.5.0
python-dotenv==1.0.0
anthropic==0.7.0
openai==1.3.0
krakenex==2.1.0
ib-insync==10.21.1
pandas==2.1.3
numpy==1.24.3

Development Workflow
1. Setup Development Environment
bash# Clone repo
git clone https://github.com/yourusername/labourious.git
cd labourious

# Backend setup
python3 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt

# Frontend setup
cd frontend
npm install
cd ..
2. Start Development Servers
bash# Terminal 1: Backend
python backend/main.py

# Terminal 2: Frontend (webpack dev server)
cd frontend && npm start
3. Run Tests
bash# Backend tests
pytest backend/tests/

# Frontend tests
cd frontend && npm test
4. Build for Production
bash# Build frontend
cd frontend && npm run build

# Create standalone executable (if desired)
pyinstaller backend/main.py --onefile

Git Workflow
main
├── [releases/v1.0.0]
├── develop
│   ├── feature/add-kraken-support
│   ├── feature/improve-warroom-ui
│   ├── bugfix/fix-position-sizing
│   └── chore/update-dependencies

Next Steps for Implementation

Week 1: Set up project structure, basic FastAPI backend, mock frontend
Week 2: Implement vault encryption, broker connectivity (IB + Kraken)
Week 3: Build warroom UI, agent inspector
Week 4: Integrate Ollama, implement agent executor
Week 5: Add backtesting, paper trading mode
Week 6: Dashboard, charts, trade history
Week 7: Testing, security audit, documentation
Week 8: Release v1.0, GitHub repository


This structure is:

✅ Scalable — easy to add new brokers, agents, features
✅ Testable — clear boundaries between components
✅ Maintainable — organized, self-documenting
✅ Professional — suitable for open-source distribution

Ready to start building? Clone the structure and begin with main.py + App.jsx.
