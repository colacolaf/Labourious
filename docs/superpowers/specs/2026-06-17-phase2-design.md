# Phase 2 Design Spec — Labourious

**Date:** 2026-06-17  
**Status:** Approved for implementation  
**Phase:** 2 of 3  
**Focus:** Backend-heavy (agent engine, brokers, WS, backtesting) + MVP warroom frontend

---

## 1. Scope Summary

Phase 2 builds on the Phase 1 foundation (FastAPI skeleton, SQLAlchemy models, encrypted vault, React shell) and delivers:

- Complete agent execution engine (orchestrator → LLM → trade executor → broker)
- Alpaca + Binance broker integrations (plus stub upgrades for Kraken/IB)
- FastAPI native WebSocket server (replace Phase 1 stub)
- Backtesting CLI (basic + walk-forward, rule-based mock LLM default)
- Paper trading mode (per-agent isolated balance, simulated slippage/commission)
- Risk management system (per-agent + portfolio-level meta-agent)
- MVP warroom frontend (isometric SVG grid, agent sprites, inspector, real-time P&L)
- Dashboard page (portfolio summary, leaderboard, equity curve)
- DB schema migration (Alembic, add missing agent fields + new tables)

**Deferred to Phase 3:** email/SMS notifications, ControlRoom settings UI, context file drag-and-drop builder, allocation pie chart, advanced analytics.

---

## 2. Architecture: Option B — Layered Modules

Each layer has one clear purpose and communicates via explicit async function calls. No shared mutable state between layers except the shared market data cache and the connection manager.

```
backend/
├── orchestrator/
│   ├── agent_orchestrator.py   # APScheduler, lifecycle, loop dispatch
│   └── risk_agent.py           # portfolio-level meta-monitoring, auto-pause
├── llm/
│   ├── llm_router.py           # routing logic, prompt build, response parse
│   ├── ollama_client.py        # httpx → localhost:11434
│   └── claude_client.py        # anthropic SDK, key from vault
├── trading/
│   ├── trade_executor.py       # order placement, stop mgmt, approval gate
│   ├── risk_manager.py         # per-agent: confidence threshold, streak, drawdown
│   └── confidence_scorer.py    # confidence formula from AGENTS.md
├── brokers/
│   ├── base.py                 # BrokerConnector ABC + MarketData/Order/Position models
│   ├── alpaca.py               # alpaca-trade-api
│   ├── binance.py              # ccxt
│   ├── kraken.py               # krakenex (upgrade from Phase 1 stub)
│   ├── interactive_brokers.py  # ib_insync (upgrade from Phase 1 stub)
│   └── manager.py              # registry dict + get_connector(broker, vault) factory
├── api/
│   ├── websocket.py            # ConnectionManager, broadcast, inbound approve_trade
│   ├── agents.py               # all agent endpoints (new + expand)
│   ├── brokers.py              # connect, status, test, accounts
│   ├── trades.py               # history, details, export CSV
│   ├── dashboard.py            # summary, performance, allocation, equity-curve
│   └── settings.py             # LLM config, vault password, capital allocation
├── scripts/
│   └── backtest.py             # CLI: basic + walk-forward backtest
└── main.py                     # add WS router, scheduler startup, all API routers
```

---

## 3. Database Migration

**Tool:** Alembic (add to requirements.txt). Single migration file for all Phase 2 changes.

### Agent model additions

| Column | Type | Default | Notes |
|---|---|---|---|
| `room` | String(50) | `"day_trading"` | day_trading / swing_trading / long_term |
| `broker` | String(50) | `"alpaca"` | maps to broker registry key |
| `context_file_path` | String(255) | null | relative path under `contexts/` |
| `confidence_score` | Integer | 10 | 10–100, formula from AGENTS.md |
| `execution_mode` | String(20) | `"human_in_loop"` | autonomous / human_in_loop / risk_based |
| `check_frequency` | Integer | 300 | seconds between agent loop runs |
| `paper_trading_balance` | Float | 100000.0 | per-agent isolated paper balance |
| `consecutive_losses` | Integer | 0 | reset to 0 on resume |
| `grid_col` | Integer | 0 | isometric grid position |
| `grid_row` | Integer | 0 | isometric grid position |
| `use_local_llm` | Boolean | True | True = Ollama, False = Claude |

### New tables

**`broker_configs`**
```sql
id, broker_name, connected_at, last_tested_at, is_active
-- NO credentials here — vault only
```

**`logs`**
```sql
id, timestamp, agent_id (nullable FK), level, message, extra_json
```

**`pending_approvals`** (in-memory dict is fine for MVP; DB fallback if restart needed)
```sql
id, trade_id, agent_id, decision_json, timeout_at, status (waiting/approved/rejected/expired)
```

---

## 4. Agent Execution Loop

```
APScheduler fires agent_id every check_frequency seconds
        │
        ▼
1. Fetch market data
   └─ Check shared cache (symbol → {data, fetched_at})
   └─ If stale (>60s): fetch from broker API, update cache
        │
        ▼
2. Load context file
   └─ Read from agent.context_file_path (relative to contexts/)
   └─ Parse variables: replace ${RSI_14}, ${MA_20}, etc. with live values
        │
        ▼
3. LLM Router → TradeDecision
   └─ build_prompt(market_data, context) → string
   └─ if agent.use_local_llm: call_ollama(prompt)
      else: call_claude(prompt)  [key from vault]
   └─ parse_decision(response) → TradeDecision (pydantic validated)
   └─ Retry up to 3× on parse failure; HOLD on final failure
        │
        ▼
4. Risk checks (risk_manager.check_agent)
   └─ confidence < 0.35 → auto-pause, WS broadcast agent_paused, return
   └─ consecutive_losses >= 3 → auto-pause, same
   └─ decision.action == HOLD → log, return
        │
        ▼
5. Approval gate (non-blocking)
   ├─ autonomous: → trade_executor.execute(decision, agent)
   └─ human_in_loop:
        └─ store in pending_approvals dict
        └─ WS broadcast agent_approval_needed
        └─ background task monitors timeout (30s → auto-reject)
        └─ return (scheduler free for next agent)
        │
        ▼
6. trade_executor.execute(decision, agent)
   └─ calculate_position_size(capital, decision.position_size, agent.max_position_size)
   └─ get_connector(agent.broker, vault) → BrokerConnector
   └─ if agent.is_paper_trading: simulate_order(agent, decision, size)
      else: connector.place_order(symbol, side, quantity)
   └─ set_stop_loss + set_take_profit
   └─ log_trade to DB
        │
        ▼
7. Post-execution
   └─ update agent.total_pnl, consecutive_losses, total_trades, winning_trades
   └─ recalculate confidence_score (confidence_scorer.py)
   └─ WS broadcast trade_executed + agent_update + portfolio_update
```

---

## 5. LLM Router

**Routing logic:** `agent.use_local_llm` flag (default True). Falls back to Claude if Ollama unreachable (connection error → retry 1× → fallback).

**Ollama:** `POST http://localhost:11434/api/generate` via httpx, `timeout=30.0`, model from settings (default `mistral`).

**Claude:** `anthropic.AsyncAnthropic`, model `claude-sonnet-4-6`, `max_tokens=500`. API key from `vault.get("anthropic_api_key")`. Never log key.

**Prompt template:**
```
You are a trading AI. Based on the rules below and market data, decide whether to BUY, SELL, or HOLD.

TRADING RULES:
{context}

CURRENT MARKET DATA:
- Symbol: {symbol}
- Price: ${price}
- RSI(14): {rsi}
- Volume: {volume}
- 20-day MA: ${ma20}
- 50-day MA: ${ma50}

Respond ONLY with valid JSON:
{"action": "BUY|SELL|HOLD", "confidence": 0.0-1.0, "position_size": 0.0-1.0, "stop_loss": -0.05, "take_profit": 0.15, "reasoning": "brief"}
```

**Parse failure handling:** regex extract JSON block from response → `TradeDecision.model_validate()`. On `ValidationError`: retry prompt with `"Your previous response was invalid JSON. Respond ONLY with the JSON object."`. After 3 failures: return `TradeDecision(action="HOLD", confidence=0.0, ...)` and log WARNING.

---

## 6. Broker Layer

### BrokerConnector ABC (`brokers/base.py`)

```python
@dataclass
class MarketData:
    symbol: str; price: float; volume: float
    rsi: float | None; ma20: float | None; ma50: float | None
    fetched_at: float  # unix timestamp

@dataclass
class Order:
    order_id: str; symbol: str; side: str
    quantity: float; filled_price: float | None; status: str

@dataclass
class Position:
    symbol: str; quantity: float; avg_price: float; unrealized_pnl: float

class BrokerConnector(ABC):
    async def get_account_balance(self) -> float: ...
    async def get_market_data(self, symbol: str) -> MarketData: ...
    async def place_order(self, symbol, side, quantity, order_type="market") -> Order: ...
    async def set_stop_loss(self, order_id: str, percent: float) -> bool: ...
    async def set_take_profit(self, order_id: str, percent: float) -> bool: ...
    async def get_positions(self) -> list[Position]: ...
    async def close_position(self, symbol: str) -> bool: ...
    async def test_connection(self) -> bool: ...
```

### Alpaca (`alpaca-trade-api`)
- Paper: base URL `https://paper-api.alpaca.markets`
- Live: base URL `https://api.alpaca.markets`
- Toggle via `agent.is_paper_trading` → passed to connector constructor
- Vault keys: `alpaca_api_key`, `alpaca_secret`

### Binance (ccxt)
- `ccxt.binance({'apiKey': ..., 'secret': ..., 'enableRateLimit': True})`
- Crypto spot only in Phase 2
- Paper mode: simulated locally (Binance has no paper account); balance tracked in `agent.paper_trading_balance`
- Vault keys: `binance_api_key`, `binance_secret`

### Vault key convention (all brokers)
```
{broker}_api_key
{broker}_secret
interactive_brokers_account_id   (IB uses local socket, no API key)
```

### Paper trading simulation
```python
# In trade_executor.py when agent.is_paper_trading:
simulated_price = market_data.price * (1 + slippage)  # default 0.001
commission = agent.config.get("commission", 10.0)
cost = simulated_price * quantity + commission
agent.paper_trading_balance -= cost  # on BUY
# Log as normal trade with is_paper=True flag on Trade record
```

---

## 7. Risk Management

### Per-agent (risk_manager.py)
- `confidence < 0.35` → auto-pause
- `consecutive_losses >= 3` → auto-pause
- `current_drawdown > agent.risk_config.max_drawdown` → auto-pause
- On pause: set `agent.status = PAUSED`, WS broadcast `agent_paused`, log to `logs` table

### Portfolio-level (risk_agent.py)
- Runs every 60s (separate APScheduler job)
- Aggregates all agents' P&L, win rates, confidence scores
- Detects portfolio drawdown exceeding `settings.MAX_PORTFOLIO_DRAWDOWN` (default -20%)
- On breach: pause ALL active agents, WS broadcast `risk_alert`
- Generates risk dashboard text (format per AGENTS.md) → stored in memory, served via `GET /api/dashboard/risk`

### On resume (POST /api/agents/{id}/resume)
```python
agent.status = IDLE
agent.consecutive_losses = 0
agent.confidence_score = 50  # fresh start
```

### Confidence scorer (confidence_scorer.py)
```
score = 10  (base)
      + min(30, connected_api_count * 5)   (API quality bonus)
      + min(20, context_detail_score * 10)  (context quality, heuristic)
      + min(40, (wins // 5) * 2)            (performance, +2% per 5 wins)
      - (losses * 2)                         (loss penalty)
      - (10 if consecutive_losses >= 3)      (streak penalty)
score = max(0, min(100, score))
```

---

## 8. WebSocket Server

**Replace** `backend/api/websocket.py` stub entirely.

```python
class ConnectionManager:
    connections: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.add(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.discard(ws)

    async def broadcast(self, msg: dict):
        dead = set()
        for ws in self.connections:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.add(ws)
        self.connections -= dead

manager = ConnectionManager()
```

**Endpoint:** `ws://localhost:8000/ws` (fix path — Phase 1 had `/ws/connect`)

**Inbound message handling:**
```python
# Only one inbound type in Phase 2:
{"type": "approve_trade", "trade_id": "...", "agent_id": "...", "approved": true/false}
# → resolves pending_approvals[trade_id]
```

**Shared instance:** `manager` imported by orchestrator and all API routers that need to broadcast.

---

## 9. Backtesting CLI

```bash
python -m backend.scripts.backtest agent.json \
  --start=2024-01-01 --end=2024-06-30 \
  --mode=basic          # or walk-forward
  --windows=4           # walk-forward only, default 4 (6:2 train:test ratio)
  --use-llm             # use real LLM instead of rule-based mock (slow)
  --output=report.json  # optional JSON export
  --csv=trades.csv      # optional CSV trade log export
```

### Data sourcing
1. If agent.broker configured and API keys in vault → fetch from broker
2. Fallback: `yfinance.download(symbol, start, end)` → OHLCV DataFrame

### Basic mode
- Load agent config + context file
- Fetch full OHLCV history for period
- Replay bar-by-bar: compute indicators (pandas-ta), substitute `${VAR}` values
- Default: rule-based mock parser — regex-extract `${VAR} > VALUE` / `${VAR} < VALUE` conditions from context file, evaluate against OHLCV indicators directly (no LLM, fast, free)
- `--use-llm`: calls LLM router per bar (real cost, real tokens, slow)
- Track paper balance, record each simulated trade
- Compute: total return, win rate, Sharpe ratio (annualized), max drawdown

### Walk-forward mode
- Split period into 4 windows, each = 75% train + 25% test
- Slide forward: window 1 trains on months 1-6, tests on 7-8; window 2 trains on 3-10, tests 11-12; etc.
- Run basic backtest on each window's test segment
- Report per-window stats + aggregate
- Walk-forward efficiency = mean(live_test_return) / mean(train_return)

### Output format
```
BACKTEST RESULTS: {agent_name}
Period: {start} → {end}  |  Mode: {mode}
─────────────────────────────────────────
Total Return:    +18.5%
Win Rate:        67% (47/70 trades)
Sharpe Ratio:    1.3
Max Drawdown:    -12.4%
Avg Trade P&L:   +$87.50
─────────────────────────────────────────
Walk-Forward Efficiency: 0.81  [window results: +21%, +15%, +18%, +20%]
─────────────────────────────────────────
Verdict: ✅ Profitable, ready to paper trade
```

---

## 10. API Endpoints (Phase 2 additions)

All existing Phase 1 endpoints unchanged. New/expanded:

### Agents
- `GET /api/agents` — list (add room/enabled filters)
- `POST /api/agents` — create (new fields: room, broker, context_file_content, config)
- `GET /api/agents/{id}` — detail with performance
- `PUT /api/agents/{id}` — update config
- `DELETE /api/agents/{id}`
- `POST /api/agents/{id}/approve` — resolve pending trade
- `POST /api/agents/{id}/toggle` — enable/disable
- `POST /api/agents/{id}/resume` — resume paused agent (resets losses + confidence)
- `POST /api/agents/{id}/update-context` — update context file content
- `GET /api/agents/{id}/trades` — trade history
- `GET /api/agents/{id}/performance` — metrics

### Brokers
- `POST /api/brokers/connect`
- `GET /api/brokers/status`
- `GET /api/brokers/{broker}/test-connection`
- `GET /api/brokers/{broker}/accounts`

### Trades
- `GET /api/trades` — all agents, filterable
- `GET /api/trades/{id}`
- `POST /api/trades/export` — CSV download

### Dashboard
- `GET /api/dashboard/summary`
- `GET /api/dashboard/performance` — leaderboard
- `GET /api/dashboard/allocation`
- `GET /api/dashboard/equity-curve`
- `GET /api/dashboard/risk` — risk agent report text

### Settings
- `GET /api/settings`
- `POST /api/settings/llm`
- `POST /api/settings/vault-password`
- `POST /api/settings/allocation`

---

## 11. Frontend (MVP)

### New components

**IsometricGrid.jsx**
- SVG viewport, pan via drag, no zoom in Phase 2
- Tile rendering: `<polygon>` for each occupied cell
- Agent sprites rendered as `<g>` groups, z-ordered by row (painter's algorithm)
- Grid coordinate math:
  ```javascript
  const TILE_W = 60, TILE_H = 30, OFFSET_X = 100, OFFSET_Y = 100;
  const toScreen = (col, row) => ({
    x: OFFSET_X + (col - row) * (TILE_W / 2),
    y: OFFSET_Y + (col + row) * (TILE_H / 2),
  });
  ```

**AgentSprite.jsx**
- SVG `<g>` with Framer Motion animations
- States: idle (y sway 3s), active (pulse ring 0.8s), paused (desaturated + pause icon)
- Hover: scale 1.1 + tooltip (name, P&L, confidence%)
- Click: `agents.store.selectAgent(id)` → opens inspector

**TradeNotification.jsx**
- Framer Motion: pop-in 0.2s → hold 2.5s → fade-out 0.5s
- Position: above agent sprite in SVG coordinate space
- Color: green (profit / BUY) or red (loss / SELL)

**ApprovalDialog.jsx**
- Full-screen modal overlay (Framer Motion slide-in from top, bounce)
- Shows: agent name, symbol, side, quantity, confidence%, reasoning
- `[✅ APPROVE]` / `[❌ REJECT]` buttons + countdown timer bar
- At 0s: auto-sends `{type: "approve_trade", approved: false}` via WS
- On button click: same WS message with user's choice, then `POST /api/agents/{id}/approve`

**AgentInspector.jsx** (slide-out panel, 380px wide, right edge)
- 5 tabs: Overview / Trades / Rules / Performance / Settings
- Framer Motion: `x: 380 → 0` on open, `x: 0 → 380` on close (0.3s ease)
- Auto-refresh every 5s while open

**Dashboard.jsx**
- 4 summary cards: total P&L, 30d return, YTD return, max drawdown
- Agent leaderboard table (sortable by return / Sharpe / win rate)
- 30-day equity curve (Recharts `LineChart`, `stroke="var(--color-primary)"`)
- Data: `GET /api/dashboard/summary` + `/performance` + `/equity-curve`

**ContextBuilder.jsx** (minimal)
- Form: agent name, room selector, broker selector, text area (context rules)
- Variable reference panel (collapsible): lists all `${VAR}` options from AGENTS.md
- Validate: non-empty name + non-empty context → `POST /api/agents`

### Existing files modified
- `WarroomDay/Swing/LongTerm.jsx` — replace `<PlaceholderPage>` with `<Warroom room="..." />`
- `App.jsx` — add `/dashboard` route, wire `ControlRoom` route to settings form
- `useWebSocket.js` — full implementation (was stub), exponential backoff reconnect
- `agents.store.js` — add `selectedAgent`, `pendingApproval`, `updateAgent`, `pauseAgent`
- `dashboard.store.js` — wire to real endpoints

### WebSocket dispatch map (useWebSocket.js)
```javascript
const handlers = {
  agent_update:         (d) => agents.updateAgent(d),
  trade_executed:       (d) => trades.addTrade(d.trade),
  agent_approval_needed:(d) => ui.setPendingApproval(d),
  agent_paused:         (d) => agents.pauseAgent(d.agent_id),
  portfolio_update:     (d) => dashboard.updateSummary(d),
  risk_alert:           (d) => ui.addToast({ type: 'error', message: d.message }),
};
```

---

## 12. Security

All Phase 1 security requirements carry forward. Phase 2 additions:

- Alpaca/Binance API keys stored in vault only (`{broker}_api_key`, `{broker}_secret`)
- No broker credentials in `broker_configs` table
- All broker connectors: never log credentials; log `broker=alpaca action=place_order` only
- LLM API keys (Anthropic/OpenAI) stored in vault only
- Paper trading balance in DB is not real money — no special protection needed
- Backtest script: reads vault for broker API keys; never writes keys to disk
- WS server: local machine only, no auth required (matches existing API design)
- Binance ccxt: `enableRateLimit=True` always

---

## 13. Testing Requirements

### Backend unit tests
- `test_llm_router.py` — mock Ollama + Claude responses, verify parse, retry logic, HOLD fallback
- `test_trade_executor.py` — mock broker connector, verify position sizing, stop/TP logic
- `test_risk_manager.py` — confidence threshold, streak detection, auto-pause trigger
- `test_confidence_scorer.py` — formula correctness, boundary values
- `test_alpaca_connector.py` — mock `alpaca-trade-api`, verify all ABC methods
- `test_binance_connector.py` — mock ccxt, verify all ABC methods
- `test_backtest.py` — basic mode + walk-forward on synthetic OHLCV data

### Backend integration tests
- `test_agent_loop.py` — full loop: mock broker data → mock LLM → mock executor → verify DB state
- `test_websocket.py` — connect, receive broadcast, send approve_trade, verify resolution

### Frontend
- Component tests: `IsometricGrid` renders tiles, `AgentSprite` animates, `AgentInspector` tabs
- WS hook test: mock WS server, verify store dispatch on each event type

---

## 14. Implementation Order (4 weeks)

**Week 1 — Agent engine core**
1. Alembic migration (add columns + new tables)
2. `brokers/base.py` ABC + `brokers/manager.py`
3. `brokers/alpaca.py` + `brokers/binance.py`
4. `llm/ollama_client.py` + `llm/claude_client.py` + `llm/llm_router.py`
5. `trading/confidence_scorer.py` + `trading/risk_manager.py`
6. `trading/trade_executor.py` (paper + live, approval gate)
7. `orchestrator/agent_orchestrator.py` (loop + scheduler)
8. Unit tests for all above

**Week 2 — WebSocket + API layer**
1. `api/websocket.py` (full ConnectionManager, replace stub)
2. `api/agents.py` (all endpoints including resume)
3. `api/brokers.py`, `api/trades.py`, `api/dashboard.py`, `api/settings.py`
4. Wire orchestrator into `main.py` lifespan startup
5. Integration tests

**Week 3 — Backtesting + risk agent + frontend core**
1. `orchestrator/risk_agent.py`
2. `scripts/backtest.py` (basic + walk-forward)
3. Frontend: `useWebSocket.js` full impl
4. Frontend: `IsometricGrid.jsx` + `AgentSprite.jsx`
5. Frontend: replace Warroom placeholders
6. Frontend: `TradeNotification.jsx` + `ApprovalDialog.jsx`

**Week 4 — Inspector + Dashboard + polish**
1. Frontend: `AgentInspector.jsx` + all 5 tabs
2. Frontend: `Dashboard.jsx`
3. Frontend: `ContextBuilder.jsx` (minimal)
4. E2E test: create agent → warroom → approve trade → notification
5. Performance test: 5+ concurrent agents
6. Bug fixes + security review

---

## 15. Success Criteria

- 5+ agents executing concurrently without scheduler blocking
- Dashboard showing live P&L updates within 200ms of trade
- Backtesting produces realistic results on synthetic + real historical data
- Paper trading tracks balance accurately with slippage + commission
- Alpaca + Binance both connect, pass `test_connection()`
- Walk-forward backtest reports per-window efficiency
- WebSocket reconnects automatically on disconnect
- Zero API keys in logs or error messages
- `pytest tests/ -v` > 80% coverage on new backend modules
