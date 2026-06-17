# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Labourious is a locally-hosted AI trading warroom: Electron desktop app (React frontend) + FastAPI Python backend. Multiple AI agents run autonomously, executing trades via broker APIs. All broker credentials are stored in an AES-256 Fernet encrypted vault on disk. No cloud dependency.

**Phase 1** (complete) — foundation: backend skeleton, DB models, vault, React shell  
**Phase 2** (next) — agent engine: strategy execution, live trading, WebSocket feed  
**Phase 3** — analytics: performance dashboards, backtesting

---

## Commands

### Backend

```bash
# Setup (from repo root)
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

# Run (uvicorn via module)
python -m backend.main
# or directly:
uvicorn backend.main:app --reload --port 8000

# Tests
pytest tests/ -v
pytest tests/test_vault.py::test_vault_encrypt_decrypt -v  # single test
pytest tests/ -k "vault" -v                                # filter by name
pytest tests/ --asyncio-mode=auto                          # async tests
```

### Frontend (from `frontend/`)

```bash
npm install
npm start              # React dev server (localhost:3000)
npm run electron:dev   # Electron + React dev (concurrent)
npm run build          # Production React build
npm run electron:build # Package Electron app
npm run lint           # ESLint
```

### Docker

```bash
cp .env.example .env   # set VAULT_PASSWORD
docker-compose up --build
```

---

## Architecture

```
React/Electron (frontend/src/)
  → axios → FastAPI (backend/main.py :8000) via uvicorn
              ├── SQLAlchemy ORM → SQLite (data/labourious.db)
              ├── EncryptedVault (backend/vault/) → vault.db  [cryptography/Fernet]
              ├── APScheduler → Agent jobs
              ├── LiteLLM → Ollama (primary) / Claude (fallback)
              ├── LangChain → multi-step agent chains (Phase 2)
              └── python-socketio → WebSocket feed (Phase 2)
```

### Backend

- **Entry**: `backend/main.py` — FastAPI app with lifespan (DB init on startup), CORS middleware
- **Config**: `backend/config.py` — `Settings` class loads all config from `.env` via `python-dotenv`
- **DB**: `backend/database/models.py` — Three SQLAlchemy models: `Agent`, `Trade`, `Performance`. `Agent` has JSON columns `strategy_config` and `risk_config`. All FK relationships use `cascade="all, delete-orphan"`.
- **Vault**: `backend/vault/encrypted_vault.py` — `EncryptedVault` class. File format: JSON header (version + base64 salt) + newline + Fernet-encrypted JSON blob. PBKDF2-SHA256, 100k iterations. `InvalidPasswordError` on wrong password, `VaultCorruptedError` on file damage.
- **Logging**: `backend/utils/logger.py` — JSON structured logs via `python-json-logger`. Never log vault contents or API keys.

### Frontend

- **Shell**: `frontend/src/App.jsx` — grid layout (topbar + sidebar + main). All routes render placeholder `<PlaceholderPage>` until Phase 2.
- **State**: `frontend/src/stores/` — Zustand stores with `devtools` middleware. `agents.store.js` wraps all CRUD + lifecycle. `dashboard.store.js` handles health + portfolio summary.
- **API client**: `frontend/src/utils/api-client.js` — axios instance at `API_BASE_URL` (default `http://localhost:8000`). Response interceptor normalizes errors to `{ message, status, data }`. Named exports: `agentsApi`, `tradesApi`, `performanceApi`, `vaultApi`, `healthApi`.
- **Styling**: CSS custom properties in `frontend/src/styles/index.css`. Retro terminal theme. Use `var(--color-*)`, `var(--font-mono)`, `var(--space-*)` — no hardcoded colors.

---

## Library Reference

### Broker Connectivity

#### ccxt (multi-exchange — primary)
Use for all exchanges except where exchange-specific features are needed.
```python
import ccxt
exchange = getattr(ccxt, exchange_name)({'apiKey': key, 'secret': secret, 'enableRateLimit': True})
balance = await exchange.fetch_balance()
order = await exchange.create_market_order('BTC/USD', 'buy', amount)
```
Always `enableRateLimit=True`. Symbol format `'BTC/USD'` normalized across all exchanges.

#### krakenex (Kraken-specific)
Use when Kraken-specific endpoints not covered by ccxt are needed (e.g., staking, funding).
```python
import krakenex
k = krakenex.API(key=vault.get('kraken_api_key'), secret=vault.get('kraken_api_secret'))
result = k.query_private('Balance')
result = k.query_public('Ticker', {'pair': 'XBTUSD'})
```
Prefer ccxt for standard trading ops. Use krakenex only for Kraken-exclusive features.

#### ib_insync (Interactive Brokers)
Requires IB Gateway running on `localhost:7497`.
```python
from ib_insync import IB, Stock, MarketOrder
ib = IB()
await ib.connectAsync('127.0.0.1', 7497, clientId=1)
contract = Stock('AAPL', 'SMART', 'USD')
order = MarketOrder('BUY', 10)
trade = ib.placeOrder(contract, order)
await ib.disconnectAsync()
```
Always disconnect in `finally`. Use `ib.reqAccountSummaryAsync()` for portfolio data.

### HTTP Clients

#### httpx (primary HTTP client)
Use for all external API calls that aren't broker-specific.
```python
import httpx
async with httpx.AsyncClient(timeout=30.0) as client:
    response = await client.get(url, headers=headers)
    response.raise_for_status()
```
Always set `timeout=30.0`. Use async client in async FastAPI routes.

#### aiohttp (streaming / WebSocket)
Use when streaming responses or WebSocket connections to external services are needed.
```python
import aiohttp
async with aiohttp.ClientSession() as session:
    async with session.ws_connect(ws_url) as ws:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                data = msg.json()
```
Prefer httpx for standard REST calls; use aiohttp only for streaming or WS connections.

### LLM / AI

#### litellm (LLM routing — primary)
Default Ollama, fall back to Claude if unreachable.
```python
from litellm import completion
response = completion(
    model="ollama/mistral",  # swap to "claude-sonnet-4-6" for fallback
    messages=[{"role": "user", "content": prompt}],
    temperature=0.7, max_tokens=500
)
return response['choices'][0]['message']['content']
```
Validate all LLM output with pydantic `TradeDecision` (`action: Literal["BUY","SELL","HOLD"]`, `confidence: float 0-1`, `position_size: float 0-1`).

#### anthropic SDK (direct Claude access)
Use when litellm routing is insufficient or Claude-specific features needed (vision, extended thinking, tool use).
```python
import anthropic
client = anthropic.Anthropic(api_key=vault.get('anthropic_api_key'))
message = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}]
)
return message.content[0].text
```
For async: use `anthropic.AsyncAnthropic`. Store API key in vault, never in env/DB.

#### langchain (multi-step agent chains)
Use for complex agent workflows requiring memory, tool chaining, or retrieval.
```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

llm = ChatAnthropic(model="claude-sonnet-4-6")
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
result = await executor.ainvoke({"input": query})
```
Use for orchestration. Prefer litellm for single-shot completions.

### Data & Analysis

#### pydantic (validation — everywhere)
Validate all API inputs, LLM outputs, and broker responses.
```python
from pydantic import BaseModel, Field
from typing import Literal

class TradeDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    reasoning: str

decision = TradeDecision.model_validate(raw_dict)
```

#### pandas-ta (technical indicators)
```python
import pandas_ta as ta
df['RSI'] = ta.rsi(df['close'], length=14)
df['MACD'] = ta.macd(df['close'])['MACD_12_26_9']
df['BB_upper'], df['BB_mid'], df['BB_lower'] = ta.bbands(df['close']).T.values[:3]
current_rsi = df['RSI'].iloc[-1]
```

#### numpy (numerical ops)
Use for position sizing calculations, returns arrays, statistical ops on price data.
```python
import numpy as np
returns = np.diff(np.log(prices))
sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
position = np.clip(raw_signal, -1.0, 1.0)
```

#### dateutil (date parsing)
Use when parsing dates from broker APIs or user input (formats vary wildly).
```python
from dateutil import parser, tz
dt = parser.parse("2024-01-15T14:30:00+00:00")
dt_local = dt.astimezone(tz.gettz('America/New_York'))
```
Use `dateutil.parser.parse` over `datetime.strptime` when format is unknown.

#### backtrader (backtesting — Phase 3)
Use for strategy backtesting against historical data.
```python
import backtrader as bt

class MyStrategy(bt.Strategy):
    def next(self):
        if self.data.close[0] > self.data.close[-1]:
            self.buy(size=1)

cerebro = bt.Cerebro()
cerebro.addstrategy(MyStrategy)
data = bt.feeds.PandasData(dataname=df)
cerebro.adddata(data)
cerebro.run()
```

### Infrastructure

#### SQLAlchemy (ORM)
Use async sessions for all FastAPI routes.
```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import selectinload

async with AsyncSession(engine) as session:
    result = await session.execute(
        select(Agent).options(selectinload(Agent.trades)).where(Agent.id == agent_id)
    )
    agent = result.scalar_one_or_none()
```

#### APScheduler (agent job scheduling)
Stagger agent start times to avoid thundering herd.
```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler
scheduler = AsyncIOScheduler()
for i, agent in enumerate(agents):
    offset = (i / len(agents)) * agent.check_frequency
    scheduler.add_job(run_agent, 'interval', seconds=agent.check_frequency,
                      args=[agent.id], id=f"agent_{agent.id}", replace_existing=True,
                      start_date=datetime.now() + timedelta(seconds=offset))
```

#### python-socketio (WebSocket — Phase 2)
```python
from python_socketio import AsyncServer
sio = AsyncServer(async_mode='asgi', cors_allowed_origins='*')
await sio.emit('trade_executed', {'agent_id': id, 'symbol': 'BTC/USD', 'pnl': 1000})
await sio.emit('agent_update', data, room=f"agent_{agent_id}")
```

#### uvicorn (ASGI server)
Configured in `backend/main.py`. For dev with reload:
```bash
uvicorn backend.main:app --reload --port 8000 --log-level info
```
Production: remove `--reload`, add `--workers 4`.

#### python-dotenv (config)
Loaded automatically by `Settings` in `backend/config.py`. Direct usage if needed:
```python
from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ
```

#### prometheus-client (metrics)
Expose `/metrics` endpoint for agent performance, trade counts, error rates.
```python
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
trades_total = Counter('trades_total', 'Total trades executed', ['agent_id', 'action'])
trade_latency = Histogram('trade_latency_seconds', 'Trade execution latency')

trades_total.labels(agent_id=agent.id, action='BUY').inc()

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

#### cryptography (vault encryption)
Already abstracted by `EncryptedVault`. Direct use only if extending vault:
```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
```

### Testing

#### pytest + responses + faker
```python
import pytest
import responses as responses_lib
from faker import Faker

fake = Faker()

@pytest.fixture
def agent_data():
    return {
        'id': str(fake.uuid4()),
        'name': fake.word(),
        'balance': fake.pyfloat(min_value=100, max_value=10000)
    }

@responses_lib.activate
def test_broker_call():
    responses_lib.add(responses_lib.GET, 'https://api.kraken.com/0/public/Ticker',
                      json={'result': {}}, status=200)
    # test code here
```
Never hit real broker APIs in tests. Use `@responses.activate` for all external HTTP.

### Frontend Libraries

#### Zustand (state management)
```javascript
import { create } from 'zustand'
import { devtools } from 'zustand/middleware'

const useAgentStore = create(devtools((set, get) => ({
  agents: [],
  fetchAgents: async () => {
    const data = await agentsApi.list()
    set({ agents: data })
  }
})))
```

#### Framer Motion (animations)
Use for panel transitions, agent status changes, trade feed entries — not decorative motion.
```jsx
import { motion, AnimatePresence } from 'framer-motion'
<motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} />
<AnimatePresence>{items.map(item => <motion.div key={item.id} layout />)}</AnimatePresence>
```

#### Recharts (charts — Phase 3)
Use for performance dashboards. Match terminal theme via `stroke="var(--color-primary)"`.
```jsx
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts'
<ResponsiveContainer width="100%" height={300}>
  <LineChart data={data}>
    <Line type="monotone" dataKey="pnl" stroke="var(--color-primary)" dot={false} />
    <XAxis dataKey="timestamp" /><YAxis /><Tooltip />
  </LineChart>
</ResponsiveContainer>
```

---

## Security Requirements

- All broker API keys stored via `EncryptedVault`, never in DB or logs
- No hardcoded secrets — all config from `.env` via `Settings`
- All HTTP requests include `timeout` (httpx default 30s)
- `ccxt` always `enableRateLimit=True`
- All API inputs validated with pydantic before use
- Error responses must not expose key material
- **OWASP**: When implementing auth, input handling, or any user-facing endpoint, fetch the relevant OWASP cheat sheet at build time (e.g., "OWASP Authentication Cheat Sheet", "OWASP Input Validation Cheat Sheet")
- **Password validation**: When adding password fields, use a validator library and document the rules. Minimum: 12 chars, uppercase, lowercase, digit, special char. Reference the specific validator's docs for the implementation pattern.
