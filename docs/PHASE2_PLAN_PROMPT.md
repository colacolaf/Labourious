# Prompt: Write Phase 2 Implementation Plan

## Context

This is Labourious — a locally-hosted AI trading warroom: Electron + React frontend + FastAPI Python backend. Multiple AI agents run autonomously, executing trades via broker APIs. All credentials stored in AES-256 Fernet encrypted vault.

**Phase 1 is complete:** FastAPI skeleton, SQLAlchemy ORM (Agent/Trade/Performance models), encrypted vault, React shell with Zustand stores (agents, dashboard, trades, ui, websocket), basic health endpoints.

**Phase 2 design spec is written and committed** at:
`docs/superpowers/specs/2026-06-17-phase2-design.md`

Read that file first — it is the source of truth for everything Phase 2 must build.

---

## Your Task

Write the full Phase 2 implementation plan to:
`docs/superpowers/plans/2026-06-17-phase2-implementation.md`

Use the `superpowers:writing-plans` skill format exactly:
- Header with Goal / Architecture / Tech Stack / Global Constraints
- File structure section (all files to create or modify, one-line responsibility each)
- 25 tasks in TDD order (write failing test → run → implement → run → commit)
- Every step has complete code, exact pytest/npm commands with expected output, exact git commit messages
- Zero placeholders — if a step changes code, show the full code

---

## Implementation Order (25 tasks)

1. `requirements.txt` — add missing packages (alpaca-trade-api, ccxt, apscheduler, pandas, pandas-ta, numpy, yfinance, anthropic, litellm, faker, responses, python-dateutil)
2. Alembic init + migration — add 11 columns to `agents` table + new `broker_configs`, `logs`, `pending_approvals` tables
3. `backend/brokers/base.py` — `BrokerConnector` ABC + `MarketData`/`Order`/`Position` dataclasses
4. `backend/brokers/alpaca.py` — alpaca-trade-api connector (paper + live)
5. `backend/brokers/binance.py` — ccxt connector (always `enableRateLimit=True`)
6. `backend/brokers/manager.py` — registry dict + `get_connector(broker, vault)` factory
7. `backend/trading/confidence_scorer.py` — confidence formula from spec
8. `backend/trading/risk_manager.py` — per-agent checks, auto-pause triggers
9. `backend/llm/ollama_client.py` + `backend/llm/claude_client.py` — httpx → Ollama, anthropic SDK → Claude
10. `backend/llm/llm_router.py` — routing, prompt build, parse, 3-retry logic, HOLD fallback
11. `backend/trading/trade_executor.py` — position sizing, paper simulation, live order, non-blocking approval gate
12. `backend/orchestrator/agent_orchestrator.py` — APScheduler, full execution loop (fetch → LLM → risk → approve → execute)
13. `backend/orchestrator/risk_agent.py` — portfolio-level meta-agent, auto-pause all on drawdown breach
14. `backend/api/websocket.py` — `ConnectionManager`, replace Phase 1 stub, endpoint at `/ws`
15. `backend/api/agents.py` — all agent endpoints including `/resume`, `/approve`, `/toggle`, `/update-context`
16. `backend/api/brokers.py` + `api/trades.py` + `api/dashboard.py` + `api/settings.py`
17. `backend/main.py` — wire all routers + scheduler startup in lifespan
18. `backend/scripts/backtest.py` — basic + walk-forward CLI (`python -m backend.scripts.backtest`)
19. `frontend/src/hooks/useWebSocket.js` — full impl: exponential backoff, store dispatch map
20. `frontend/src/components/Warroom/IsometricGrid.jsx` + `AgentSprite.jsx`
21. `frontend/src/components/Warroom/TradeNotification.jsx` + `ApprovalDialog.jsx`
22. `frontend/src/components/Inspector/AgentInspector.jsx` + 5 tabs (Overview/Trades/Rules/Performance/Settings)
23. `frontend/src/pages/Dashboard.jsx` — 4 stat cards + leaderboard + equity curve
24. `frontend/src/pages/Warroom.jsx` + `frontend/src/components/ContextBuilder/ContextBuilder.jsx`
25. `frontend/src/App.jsx` wiring + integration tests

---

## Key Technical Details

Read the spec for full details. Critical excerpts:

**New Agent columns (Alembic migration):**
room, broker, context_file_path, confidence_score, execution_mode, check_frequency, paper_trading_balance, consecutive_losses, grid_col, grid_row, use_local_llm

**BrokerConnector ABC (base.py):**
```python
from dataclasses import dataclass
from abc import ABC, abstractmethod

@dataclass
class MarketData:
    symbol: str; price: float; volume: float
    rsi: float | None; ma20: float | None; ma50: float | None
    fetched_at: float

@dataclass
class Order:
    order_id: str; symbol: str; side: str
    quantity: float; filled_price: float | None; status: str

@dataclass
class Position:
    symbol: str; quantity: float; avg_price: float; unrealized_pnl: float

class BrokerConnector(ABC):
    @abstractmethod
    async def get_account_balance(self) -> float: ...
    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData: ...
    @abstractmethod
    async def place_order(self, symbol, side, quantity, order_type="market") -> Order: ...
    @abstractmethod
    async def set_stop_loss(self, order_id: str, percent: float) -> bool: ...
    @abstractmethod
    async def set_take_profit(self, order_id: str, percent: float) -> bool: ...
    @abstractmethod
    async def get_positions(self) -> list[Position]: ...
    @abstractmethod
    async def close_position(self, symbol: str) -> bool: ...
    @abstractmethod
    async def test_connection(self) -> bool: ...
```

**TradeDecision (pydantic):**
```python
from pydantic import BaseModel, Field
from typing import Literal

class TradeDecision(BaseModel):
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0.0, le=1.0)
    position_size: float = Field(ge=0.0, le=1.0)
    stop_loss: float = Field(default=-0.05)
    take_profit: float = Field(default=0.15)
    reasoning: str = ""
```

**Confidence formula:**
```python
score = 10
score += min(30, connected_api_count * 5)
score += min(20, context_detail_score * 10)
score += min(40, (wins // 5) * 2)
score -= (losses * 2)
score -= (10 if consecutive_losses >= 3 else 0)
score = max(0, min(100, score))
```

**WebSocket ConnectionManager:**
```python
class ConnectionManager:
    def __init__(self): self.connections: set = set()
    async def connect(self, ws):
        await ws.accept(); self.connections.add(ws)
    def disconnect(self, ws): self.connections.discard(ws)
    async def broadcast(self, msg: dict):
        dead = set()
        for ws in self.connections:
            try: await ws.send_json(msg)
            except Exception: dead.add(ws)
        self.connections -= dead
manager = ConnectionManager()
```

**Isometric grid math:**
```javascript
const TILE_W = 60, TILE_H = 30, OFFSET_X = 100, OFFSET_Y = 100;
const toScreen = (col, row) => ({
  x: OFFSET_X + (col - row) * (TILE_W / 2),
  y: OFFSET_Y + (col + row) * (TILE_H / 2),
});
```

**useWebSocket dispatch map:**
```javascript
const handlers = {
  agent_update:          (d) => agentsStore.getState().updateAgent(d),
  trade_executed:        (d) => tradesStore.getState().addTrade(d.trade),
  agent_approval_needed: (d) => uiStore.getState().setPendingApproval(d),
  agent_paused:          (d) => agentsStore.getState().pauseAgent(d.agent_id),
  portfolio_update:      (d) => dashboardStore.getState().updatePortfolioLocally(d),
  risk_alert:            (d) => uiStore.getState().addNotification({ type: 'error', message: d.message }),
};
```

**Paper trading simulation:**
```python
slippage = agent.strategy_config.get("slippage", 0.001)
commission = agent.strategy_config.get("commission", 10.0)
simulated_price = market_data.price * (1 + slippage)
cost = simulated_price * quantity + commission
agent.paper_trading_balance -= cost  # BUY
```

**Settings to add to config.py:**
- `OLLAMA_BASE_URL` = `"http://localhost:11434"`
- `OLLAMA_MODEL` = `"mistral"`
- `MAX_PORTFOLIO_DRAWDOWN` = `-0.20`
- `APPROVAL_TIMEOUT_SECONDS` = `30`
- `MARKET_DATA_CACHE_TTL` = `60`

**Security rules (CLAUDE.md — non-negotiable):**
- All broker/LLM API keys in vault only — never DB, never logs
- `ccxt` always `enableRateLimit=True`
- All API inputs validated with pydantic before use
- Error responses must not expose key material
- `httpx` always `timeout=30.0`

---

## After Writing

Commit the plan:
```bash
git add docs/superpowers/plans/2026-06-17-phase2-implementation.md
git commit -m "docs: add Phase 2 implementation plan"
git push origin main
```

Then offer to begin executing tasks.
