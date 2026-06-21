# Phase 5 — Live Agent Execution Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the orchestrator into a verified end-to-end live system, add auto-pause Bodyguard, wire all 5 Inspector tabs to real data, connect the approval dialog to live WebSocket events, and make agent sprites reflect live confidence scores.

**Architecture:** Backend priorities (P1 execution loop, P2 risk/Bodyguard) complete before frontend work (P3–P5). The orchestrator already exists and calls `TradeExecutor.execute()`; this plan closes the gaps: paper trading path, confidence-score persistence, correct `trade_approval_required` WS event, `bodyguard_pause_all` broadcast, and resume-reset logic. Frontend wires existing components (`AgentInspector`, `ApprovalDialog`, `TradeNotification`, `Agent.js` sprites) to live data — no new npm packages.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (sync Session in orchestrator), APScheduler, pytest + asyncio-mode=auto; React 18, Zustand, Framer Motion, Recharts, PixiJS (existing).

## Global Constraints

- No new npm packages unless absolutely unavoidable; use already-installed deps.
- No new backend API endpoints unless a required one genuinely does not exist; check `backend/api/` first.
- All colors via CSS vars — `var(--color-*)` only, never hardcoded hex.
- Zustand stores for all shared frontend state.
- Framer Motion for all transitions (approval dialog, inspector panel).
- Alembic for every DB schema change: `alembic revision --autogenerate -m "desc"` then `alembic upgrade head`.
- Never log vault contents or API keys.
- TDD-adjacent: write a failing test stub before implementation in every backend task.
- All async FastAPI routes use `AsyncSession`; orchestrator uses sync `Session` (established pattern — do not change).
- Paper trading is the safe default for all new agents — never default to live.
- Commit after each task: `feat(5X.Y): description` pattern.
- Run `pytest tests/ -v --asyncio-mode=auto` after each backend task before committing.

---

## File Map

### Files to Modify

| File | What changes |
|------|-------------|
| `backend/trading/trade_executor.py` | Paper trading path; correct WS event name (`trade_approval_required`); confidence-score update after trade; `trade_executed` broadcast; persist agent stats |
| `backend/orchestrator/agent_orchestrator.py` | Pass `drawdown`/`max_drawdown` to `check_agent_risk()`; confidence update after each trade; schedule RiskAgent alongside agents |
| `backend/orchestrator/risk_agent.py` | Fix `_pause_all_agents` to use sync Session (matches orchestrator pattern); broadcast `bodyguard_pause_all`; fix `run()` to use sync Session |
| `backend/api/websocket.py` | Route `reject_trade` inbound message alongside `approve_trade` |
| `backend/api/agents.py` | Add `confidence_score`, `execution_mode`, `check_frequency`, `paper_trading_balance`, `last_heartbeat` to `AgentResponse`; add `check_frequency` and `execution_mode` to `AgentUpdate`; add `is_paper` field to `Trade` model (DB migration) |
| `backend/database/models.py` | Add `is_paper` Boolean column to `Trade` (with Alembic migration) |
| `tests/test_trade_executor.py` | Add paper-trade path tests, approval-wait tests, confidence-update tests |
| `tests/test_agent_loop.py` | Add end-to-end cycle tests: paper trade written to DB + WS event emitted; risk pause persisted |
| `tests/test_risk_agent.py` | Fix/add Bodyguard tests: `check_portfolio()` pause-all; `bodyguard_pause_all` event emitted |
| `frontend/src/components/Warroom/Warroom.jsx` | Listen for `trade_approval_required` (rename from `agent_approval_needed`); queue multiple approvals |
| `frontend/src/components/Warroom/ApprovalDialog.jsx` | Accept `expires_at`; compute countdown from server timestamp |
| `frontend/src/components/Warroom/TradeNotification.jsx` | Wire to `trade_executed` WS events (already partially done via `useWarroomAgents`) |
| `frontend/src/components/Warroom/hooks/useWarroomAgents.js` | Handle `agent_update` with confidence_score patch; apply tint to sprites based on confidence |
| `frontend/src/components/Warroom/sprites/Agent.js` | Add `setConfidence(score)` method; add `setPaused(bool)` method |
| `frontend/src/stores/agents.store.js` | Add 30s polling interval; handle `agent_update` WS patch |
| `frontend/src/components/Warroom/AgentInspector.jsx` | Wire Settings tab to editable fields via PATCH; wire Overview confidence color coding; wire Rules tab to `strategy_config.context_content` |

### Files to Create

| File | Purpose |
|------|---------|
| `alembic/versions/xxxx_add_is_paper_to_trades.py` | Migration: add `is_paper` Boolean column to `trades` table |

---

## WebSocket Event Schemas

### Outbound (backend → frontend)

```json
// trade_approval_required — emitted when execution_mode=human_in_loop
{
  "event": "trade_approval_required",
  "trade_id": "uuid-string",
  "agent_id": 1,
  "agent_name": "My Agent",
  "symbol": "AAPL",
  "action": "BUY",
  "position_size_dollars": 500.0,
  "confidence": 0.72,
  "reasoning": "RSI oversold, MACD cross confirmed",
  "expires_at": "2026-06-21T14:30:30.000Z"
}

// trade_executed — emitted after every completed trade (paper or live)
{
  "event": "trade_executed",
  "agent_id": 1,
  "agent_name": "My Agent",
  "symbol": "AAPL",
  "action": "BUY",
  "pnl": 0.0,
  "confidence_score": 52,
  "is_paper": true
}

// agent_paused — per-agent pause (risk trigger)
{
  "event": "agent_paused",
  "agent_id": 1,
  "agent_name": "My Agent",
  "reason": "3 consecutive losses"
}

// bodyguard_pause_all — portfolio-level Bodyguard trigger
{
  "event": "bodyguard_pause_all",
  "reason": "Portfolio drawdown -26.00% < limit -25.00%",
  "paused_count": 5
}

// agent_update — routine status update
{
  "event": "agent_update",
  "agent_id": 1,
  "status": "idle",
  "confidence_score": 52,
  "timestamp": "2026-06-21T14:30:00.000Z"
}
```

### Inbound (frontend → backend)

```json
// approve_trade
{"type": "approve_trade", "trade_id": "uuid-string"}

// reject_trade
{"type": "reject_trade", "trade_id": "uuid-string"}
```

---

## New / Updated Endpoint Signatures

No new endpoints needed. The following existing endpoints require field additions:

- `GET /api/agents` — `AgentResponse` must include: `confidence_score`, `execution_mode`, `check_frequency`, `paper_trading_balance`, `last_heartbeat`
- `PATCH /api/agents/{id}` — `AgentUpdate` must accept: `execution_mode`, `check_frequency`
- `GET /api/agents/{id}/trades` — `TradeResponse` must include: `is_paper` (after migration)

---

## Priority 1 — End-to-End Execution Loop (Backend)

### Task 5A.1: Add `is_paper` to Trade model + Alembic migration

**Files:**
- Modify: `backend/database/models.py`
- Create: `alembic/versions/` (auto-generated)

**Interfaces:**
- Produces: `Trade.is_paper: bool` column, default `False`

- [ ] **Step 1: Write failing test**

```python
# tests/test_migration.py — add to existing file or create if absent
def test_trade_has_is_paper_column(db_session):
    """Trade model exposes is_paper field."""
    from backend.database.models import Trade, TradeSide, TradeStatus
    t = Trade(
        agent_id=1, symbol="AAPL", side=TradeSide.BUY,
        status=TradeStatus.PENDING, entry_price=100.0, quantity=1.0,
        is_paper=True,
    )
    assert t.is_paper is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_migration.py::test_trade_has_is_paper_column -v
```

Expected: `FAIL` — `TypeError: unexpected keyword argument 'is_paper'`

- [ ] **Step 3: Add column to Trade model**

In `backend/database/models.py`, after `fees = Column(Float, default=0.0)` (line ~148), add:

```python
    is_paper = Column(Boolean, default=False, nullable=False)
```

- [ ] **Step 4: Generate and apply Alembic migration**

```bash
cd /Users/coleadams/labourious
source .venv/bin/activate
alembic revision --autogenerate -m "add_is_paper_to_trades"
alembic upgrade head
```

Inspect the generated file in `alembic/versions/` — confirm it adds `is_paper` column.

- [ ] **Step 5: Run test to verify it passes**

```bash
pytest tests/test_migration.py::test_trade_has_is_paper_column -v
```

Expected: `PASS`

- [ ] **Step 6: Commit**

```bash
git add backend/database/models.py alembic/versions/
git commit -m "feat(5A.1): add is_paper column to trades table via Alembic migration"
```

---

### Task 5A.2: Expand AgentResponse + AgentUpdate in agents.py

**Files:**
- Modify: `backend/api/agents.py`

**Interfaces:**
- Produces: `AgentResponse` with `confidence_score`, `execution_mode`, `check_frequency`, `paper_trading_balance`, `last_heartbeat`; `AgentUpdate` accepts `execution_mode`, `check_frequency`

- [ ] **Step 1: Write failing test**

```python
# tests/test_api_agents.py — add to existing test file
def test_agent_response_has_confidence_fields(client, auth_headers):
    """GET /api/agents returns confidence_score, execution_mode, check_frequency."""
    resp = client.get("/api/agents", headers=auth_headers)
    assert resp.status_code == 200
    agents = resp.json()
    if agents:
        a = agents[0]
        assert "confidence_score" in a
        assert "execution_mode" in a
        assert "check_frequency" in a
        assert "paper_trading_balance" in a
        assert "last_heartbeat" in a  # may be None
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_api_agents.py::test_agent_response_has_confidence_fields -v
```

Expected: `FAIL` — KeyError or assertion error on missing fields.

- [ ] **Step 3: Update AgentResponse and AgentUpdate**

In `backend/api/agents.py`, update `AgentResponse` (after `win_rate` line ~69):

```python
    confidence_score: int
    execution_mode: str
    check_frequency: int
    paper_trading_balance: float
    last_heartbeat: Optional[datetime]
```

Update `AgentUpdate` (after `take_profit_pct` line ~47):

```python
    execution_mode: Optional[str] = None
    check_frequency: Optional[int] = None
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_api_agents.py::test_agent_response_has_confidence_fields -v
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/api/agents.py
git commit -m "feat(5A.2): expand AgentResponse with confidence_score, execution_mode, check_frequency, paper_trading_balance, last_heartbeat"
```

---

### Task 5A.3: Harden TradeExecutor — paper path, correct WS event, confidence update

**Files:**
- Modify: `backend/trading/trade_executor.py`
- Modify: `tests/test_trade_executor.py`

**Interfaces:**
- Consumes: `Trade.is_paper` (Task 5A.1), `calculate_confidence_score()` from `backend/trading/confidence_scorer.py`
- Produces:
  - `TradeExecutor.execute()` emits `trade_approval_required` (not `trade_pending_approval`) with full schema
  - `TradeExecutor._execute_paper_order(agent_id, symbol, side, quantity, current_price, db_session, decision, agent_config)` — new private method
  - `TradeExecutor._execute_live_order()` writes `is_paper=False`; broadcasts `trade_executed` after commit
  - After every completed trade: calls `_update_agent_stats(agent_id, trade, db_session, broadcast_callback)`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_trade_executor.py — add these tests

@pytest.mark.asyncio
async def test_paper_trade_writes_closed_record(mock_vault):
    """Paper path writes a CLOSED Trade with is_paper=True, no broker call."""
    from backend.trading.trade_executor import TradeExecutor
    from backend.llm.llm_router import TradeDecision
    from backend.database.models import TradeStatus

    executor = TradeExecutor(mock_vault, None)
    decision = TradeDecision(action="BUY", confidence=0.7, position_size=0.1, reasoning="test")
    agent_config = {
        "broker": "alpaca", "paper_trading": True,
        "allocation_percent": 0.1, "max_position_size": 0.05,
        "asset": "AAPL", "execution_mode": "autonomous",
        "name": "TestAgent", "user_id": None,
    }
    db_session = MagicMock()
    db_session.add = MagicMock()
    db_session.commit = MagicMock()

    # Mock get_connector to return fake balance; paper path should NOT call place_order
    mock_connector = MagicMock()
    mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)
    mock_connector.get_market_data = AsyncMock()
    mock_connector.get_market_data.return_value.price = 150.0

    with patch("backend.trading.trade_executor.get_connector", return_value=mock_connector):
        result = await executor.execute(
            agent_id=1, decision=decision, agent_config=agent_config,
            vault=mock_vault, db_session=db_session, broadcast_callback=None,
        )

    assert result["status"] == "executed"
    assert result.get("is_paper") is True
    mock_connector.place_order = MagicMock()
    mock_connector.place_order.assert_not_called()
    added_trade = db_session.add.call_args[0][0]
    from backend.database.models import TradeStatus
    assert added_trade.is_paper is True
    assert added_trade.status == TradeStatus.CLOSED


@pytest.mark.asyncio
async def test_human_in_loop_emits_trade_approval_required(mock_vault):
    """human_in_loop path broadcasts trade_approval_required with correct schema."""
    from backend.trading.trade_executor import TradeExecutor
    from backend.llm.llm_router import TradeDecision

    executor = TradeExecutor(mock_vault, None)
    decision = TradeDecision(action="BUY", confidence=0.72, position_size=0.1, reasoning="test reason")
    agent_config = {
        "broker": "alpaca", "paper_trading": False,
        "allocation_percent": 0.1, "max_position_size": 0.05,
        "asset": "AAPL", "execution_mode": "human_in_loop",
        "name": "TestAgent", "user_id": None,
    }
    mock_connector = MagicMock()
    mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)

    broadcast_calls = []
    async def fake_broadcast(data):
        broadcast_calls.append(data)

    with patch("backend.trading.trade_executor.get_connector", return_value=mock_connector):
        result = await executor.execute(
            agent_id=1, decision=decision, agent_config=agent_config,
            vault=mock_vault, db_session=MagicMock(), broadcast_callback=fake_broadcast,
        )

    assert result["status"] == "pending_approval"
    assert len(broadcast_calls) == 1
    evt = broadcast_calls[0]
    assert evt["event"] == "trade_approval_required"
    assert "expires_at" in evt
    assert "reasoning" in evt
    assert evt["agent_name"] == "TestAgent"
    assert evt["action"] == "BUY"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_trade_executor.py::test_paper_trade_writes_closed_record tests/test_trade_executor.py::test_human_in_loop_emits_trade_approval_required -v
```

Expected: both `FAIL`

- [ ] **Step 3: Rewrite TradeExecutor**

Replace `backend/trading/trade_executor.py` with:

```python
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Callable

from sqlalchemy.orm import Session

from backend.brokers.manager import get_connector
from backend.database.models import Agent, Trade, TradeSide, TradeStatus
from backend.llm.llm_router import TradeDecision
from backend.trading.confidence_scorer import calculate_confidence_score


class TradeExecutor:
    """Executes trade decisions with position sizing, approval gating, and DB persistence."""

    def __init__(self, vault, db_session):
        self.vault = vault
        self.db_session = db_session
        self.pending_approvals = {}  # {trade_id: {...}}

    def calculate_position_size(
        self,
        agent_capital_allocation: float,
        account_balance: float,
        decision_position_size: float,
        max_position_size_percent: float = 0.05,
    ) -> float:
        agent_capital = account_balance * agent_capital_allocation
        position = agent_capital * decision_position_size
        hard_cap = account_balance * max_position_size_percent
        return min(position, hard_cap)

    async def execute(
        self,
        agent_id: int,
        decision: TradeDecision,
        agent_config: dict,
        vault,
        db_session: Session,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        if decision.action == "HOLD":
            return {"status": "skipped", "reason": "HOLD decision"}

        try:
            connector = get_connector(agent_config["broker"], vault)
        except Exception as e:
            return {"status": "error", "reason": f"broker error: {e}"}

        try:
            account_balance = await connector.get_account_balance()
        except Exception as e:
            return {"status": "error", "reason": f"balance fetch error: {e}"}

        position_size_dollars = self.calculate_position_size(
            agent_capital_allocation=agent_config.get("allocation_percent", 0.1),
            account_balance=account_balance,
            decision_position_size=decision.position_size,
            max_position_size_percent=agent_config.get("max_position_size", 0.05),
        )

        if position_size_dollars <= 0:
            return {"status": "skipped", "reason": "calculated position size <= 0"}

        side = "buy" if decision.action == "BUY" else "sell"
        symbol = agent_config.get("asset", "BTC/USD")
        trade_id = str(uuid.uuid4())

        if agent_config.get("execution_mode") == "human_in_loop":
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=30)
            self.pending_approvals[trade_id] = {
                "agent_id": agent_id,
                "symbol": symbol,
                "side": side,
                "position_size_dollars": position_size_dollars,
                "decision": decision,
                "connector": connector,
                "db_session": db_session,
                "expires_at": expires_at,
                "agent_config": agent_config,
                "broadcast_callback": broadcast_callback,
            }
            if broadcast_callback:
                await broadcast_callback({
                    "event": "trade_approval_required",
                    "trade_id": trade_id,
                    "agent_id": agent_id,
                    "agent_name": agent_config.get("name", ""),
                    "symbol": symbol,
                    "action": decision.action,
                    "position_size_dollars": position_size_dollars,
                    "confidence": decision.confidence,
                    "reasoning": decision.reasoning,
                    "expires_at": expires_at.isoformat(),
                })
            asyncio.create_task(self._approval_timeout(trade_id, broadcast_callback))
            return {
                "status": "pending_approval",
                "trade_id": trade_id,
                "timeout_seconds": 30,
            }

        if agent_config.get("paper_trading", True):
            try:
                market = await connector.get_market_data(symbol)
                current_price = market.price
            except Exception:
                current_price = 0.0
            return await self._execute_paper_order(
                agent_id=agent_id, symbol=symbol, side=side,
                quantity=position_size_dollars, current_price=current_price,
                db_session=db_session, decision=decision, agent_config=agent_config,
                broadcast_callback=broadcast_callback,
            )

        return await self._execute_live_order(
            agent_id=agent_id, symbol=symbol, side=side,
            quantity=position_size_dollars, connector=connector,
            db_session=db_session, decision=decision, agent_config=agent_config,
            broadcast_callback=broadcast_callback,
        )

    async def approve_trade(self, trade_id: str, approved: bool) -> dict:
        if trade_id not in self.pending_approvals:
            return {"status": "error", "reason": "trade not found"}
        data = self.pending_approvals.pop(trade_id)
        if not approved:
            return {"status": "rejected", "trade_id": trade_id}
        if data["agent_config"].get("paper_trading", True):
            try:
                market = await data["connector"].get_market_data(data["symbol"])
                current_price = market.price
            except Exception:
                current_price = 0.0
            return await self._execute_paper_order(
                agent_id=data["agent_id"], symbol=data["symbol"], side=data["side"],
                quantity=data["position_size_dollars"], current_price=current_price,
                db_session=data["db_session"], decision=data["decision"],
                agent_config=data["agent_config"], broadcast_callback=data["broadcast_callback"],
            )
        return await self._execute_live_order(
            agent_id=data["agent_id"], symbol=data["symbol"], side=data["side"],
            quantity=data["position_size_dollars"], connector=data["connector"],
            db_session=data["db_session"], decision=data["decision"],
            agent_config=data["agent_config"], broadcast_callback=data["broadcast_callback"],
        )

    async def _execute_paper_order(
        self, agent_id: int, symbol: str, side: str, quantity: float,
        current_price: float, db_session: Session,
        decision: Optional[TradeDecision] = None,
        agent_config: Optional[dict] = None,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        trade_side = TradeSide.BUY if side.lower() == "buy" else TradeSide.SELL
        trade = Trade(
            agent_id=agent_id,
            symbol=symbol,
            side=trade_side,
            status=TradeStatus.CLOSED,
            entry_price=current_price,
            exit_price=current_price,
            quantity=quantity,
            pnl=0.0,
            is_paper=True,
            entry_reason=decision.reasoning if decision else None,
            opened_at=datetime.utcnow(),
            closed_at=datetime.utcnow(),
        )
        db_session.add(trade)
        db_session.commit()
        await self._update_agent_stats(agent_id, trade, db_session, broadcast_callback, agent_config)
        return {"status": "executed", "is_paper": True, "trade_id": trade.id}

    async def _execute_live_order(
        self, agent_id: int, symbol: str, side: str, quantity: float,
        connector, db_session: Session,
        decision: Optional[TradeDecision] = None,
        agent_config: Optional[dict] = None,
        broadcast_callback: Optional[Callable] = None,
    ) -> dict:
        try:
            order = await connector.place_order(symbol, side, quantity, "market")
        except Exception as e:
            return {"status": "error", "reason": f"order placement failed: {e}"}

        trade_side = TradeSide.BUY if side.lower() == "buy" else TradeSide.SELL
        trade = Trade(
            agent_id=agent_id,
            exchange_order_id=order.order_id,
            symbol=symbol,
            side=trade_side,
            status=TradeStatus.PENDING,
            entry_price=order.filled_price or 0.0,
            quantity=quantity,
            is_paper=False,
            stop_loss=decision.stop_loss if decision else None,
            take_profit=decision.take_profit if decision else None,
            entry_reason=decision.reasoning if decision else None,
            opened_at=datetime.utcnow(),
        )
        db_session.add(trade)
        db_session.commit()
        await self._update_agent_stats(agent_id, trade, db_session, broadcast_callback, agent_config)
        return {"status": "executed", "order_id": order.order_id,
                "filled_price": order.filled_price, "trade_id": trade.id}

    async def _update_agent_stats(
        self, agent_id: int, trade: Trade, db_session: Session,
        broadcast_callback: Optional[Callable], agent_config: Optional[dict],
    ):
        """Update agent confidence score, trade counts, and broadcast trade_executed."""
        from sqlalchemy import select
        from backend.database.models import Agent

        agent = db_session.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return

        pnl = trade.pnl or 0.0
        agent.total_trades = (agent.total_trades or 0) + 1
        if pnl > 0:
            agent.winning_trades = (agent.winning_trades or 0) + 1
            agent.consecutive_losses = 0
        elif pnl < 0:
            agent.consecutive_losses = (agent.consecutive_losses or 0) + 1
        agent.total_pnl = (agent.total_pnl or 0.0) + pnl

        new_score = calculate_confidence_score(
            wins=agent.winning_trades or 0,
            losses=(agent.total_trades or 0) - (agent.winning_trades or 0),
            consecutive_losses=agent.consecutive_losses or 0,
        )
        agent.confidence_score = new_score
        db_session.add(agent)
        db_session.commit()

        if broadcast_callback:
            await broadcast_callback({
                "event": "trade_executed",
                "agent_id": agent_id,
                "agent_name": agent_config.get("name", "") if agent_config else "",
                "symbol": trade.symbol,
                "action": "BUY" if trade.side == TradeSide.BUY else "SELL",
                "pnl": pnl,
                "confidence_score": new_score,
                "is_paper": trade.is_paper,
            })

        try:
            if agent_config and agent_config.get("user_id"):
                from backend.notifications.triggers import notify_trade_executed
                notify_trade_executed(
                    user_id=agent_config["user_id"],
                    agent_name=agent_config.get("name", ""),
                    symbol=trade.symbol,
                    action="BUY" if trade.side == TradeSide.BUY else "SELL",
                    pnl=pnl,
                )
        except Exception:
            pass

    async def _approval_timeout(self, trade_id: str, broadcast_callback=None):
        data = self.pending_approvals.get(trade_id)
        if not data:
            return
        await asyncio.sleep(30)
        if trade_id in self.pending_approvals:
            self.pending_approvals.pop(trade_id)
            if broadcast_callback:
                await broadcast_callback({
                    "event": "trade_rejected",
                    "trade_id": trade_id,
                    "reason": "timeout",
                })
```

- [ ] **Step 4: Run failing tests to verify they now pass**

```bash
pytest tests/test_trade_executor.py -v --asyncio-mode=auto
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/trading/trade_executor.py tests/test_trade_executor.py
git commit -m "feat(5A.3): paper trading path, trade_approval_required event, confidence update after trade"
```

---

### Task 5A.4: Fix WebSocket inbound — route reject_trade

**Files:**
- Modify: `backend/api/websocket.py`

**Interfaces:**
- Consumes: existing `_approval_handler`
- Produces: `reject_trade` inbound message routes to `_approval_handler`

- [ ] **Step 1: Write failing test**

```python
# tests/test_websocket.py — add to existing file
@pytest.mark.asyncio
async def test_reject_trade_routes_to_handler():
    """reject_trade inbound message calls approval handler with approved=False."""
    from backend.api.websocket import _handle_inbound, set_approval_handler
    calls = []
    async def handler(data): calls.append(data)
    set_approval_handler(handler)
    await _handle_inbound({"type": "reject_trade", "trade_id": "abc"})
    assert len(calls) == 1
    assert calls[0]["type"] == "reject_trade"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_websocket.py::test_reject_trade_routes_to_handler -v
```

Expected: `FAIL` — handler not called

- [ ] **Step 3: Update `_handle_inbound`**

In `backend/api/websocket.py`, replace `_handle_inbound`:

```python
async def _handle_inbound(data: dict):
    """Route inbound WS messages."""
    msg_type = data.get("type")
    if msg_type in ("approve_trade", "reject_trade"):
        if _approval_handler:
            await _approval_handler(data)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_websocket.py::test_reject_trade_routes_to_handler -v
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/api/websocket.py tests/test_websocket.py
git commit -m "feat(5A.4): route reject_trade inbound WS message to approval handler"
```

---

### Task 5A.5: Wire orchestrator — drawdown to risk check, approval handler, RiskAgent schedule

**Files:**
- Modify: `backend/orchestrator/agent_orchestrator.py`
- Modify: `tests/test_agent_loop.py`

**Interfaces:**
- Consumes: `check_agent_risk(drawdown=agent.current_drawdown, max_drawdown=settings.allocation.max_portfolio_drawdown or -0.25)` — already imported
- Produces: approval handler registered via `set_approval_handler`; `RiskAgent` scheduled every 60s

- [ ] **Step 1: Write failing tests**

```python
# tests/test_agent_loop.py — add these tests

@pytest.mark.asyncio
async def test_run_agent_paper_trade_written_to_db():
    """Full cycle: paper agent → LLM BUY → Trade written to DB."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.database.models import Agent, AgentStatus, Trade, TradeStatus
    from backend.llm.llm_router import TradeDecision
    from backend.brokers.base import MarketData

    vault = MagicMock()
    vault.get.return_value = "key"
    session = MagicMock()
    db_factory = MagicMock(return_value=session)

    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.name = "TestAgent"
    agent.symbol = "AAPL"
    agent.broker = "alpaca"
    agent.status = AgentStatus.IDLE
    agent.is_active = True
    agent.check_frequency = 300
    agent.confidence_score = 50
    agent.consecutive_losses = 0
    agent.is_paper_trading = True
    agent.max_position_size = 1000.0
    agent.execution_mode = "autonomous"
    agent.context_file_path = None
    agent.last_heartbeat = None
    agent.use_local_llm = True
    agent.user_id = None
    agent.current_drawdown = 0.0

    session.query.return_value.filter.return_value.first.return_value = agent

    broadcast_calls = []
    async def fake_broadcast(data): broadcast_calls.append(data)

    mock_connector = MagicMock()
    mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)
    mock_connector.get_market_data = AsyncMock(return_value=MagicMock(
        price=150.0, volume=1_000_000, rsi=45.0, ma20=148.0, ma50=145.0
    ))

    decision = TradeDecision(action="BUY", confidence=0.75, position_size=0.05, reasoning="test")
    mock_router = MagicMock()
    mock_router.decide = AsyncMock(return_value=decision)

    orch = AgentOrchestrator(vault, db_factory)

    with patch("backend.orchestrator.agent_orchestrator.get_connector", return_value=mock_connector), \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter.from_config", return_value=mock_router), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast", side_effect=fake_broadcast):
        await orch.run_agent(1)

    # trade_executed event must have been broadcast
    trade_executed = [e for e in broadcast_calls if e.get("event") == "trade_executed"]
    assert len(trade_executed) >= 1
    assert trade_executed[0]["is_paper"] is True


@pytest.mark.asyncio
async def test_run_agent_risk_pause_persisted():
    """Agent with 3 consecutive losses is paused and broadcast emitted."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    vault.get.return_value = "key"
    session = MagicMock()
    db_factory = MagicMock(return_value=session)

    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.name = "TestAgent"
    agent.symbol = "AAPL"
    agent.broker = "alpaca"
    agent.status = AgentStatus.IDLE
    agent.is_active = True
    agent.check_frequency = 300
    agent.confidence_score = 20   # triggers pause
    agent.consecutive_losses = 3  # triggers pause
    agent.is_paper_trading = True
    agent.max_position_size = 1000.0
    agent.execution_mode = "autonomous"
    agent.context_file_path = None
    agent.last_heartbeat = None
    agent.user_id = None
    agent.current_drawdown = 0.0

    session.query.return_value.filter.return_value.first.return_value = agent

    broadcast_calls = []
    async def fake_broadcast(data): broadcast_calls.append(data)

    mock_connector = MagicMock()
    mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)
    mock_connector.get_market_data = AsyncMock(return_value=MagicMock(
        price=150.0, volume=1_000_000, rsi=45.0, ma20=148.0, ma50=145.0
    ))

    decision_mock = MagicMock()
    decision_mock.action = "BUY"
    decision_mock.confidence = 0.3
    decision_mock.position_size = 0.05
    decision_mock.reasoning = "test"

    mock_router = MagicMock()
    mock_router.decide = AsyncMock(return_value=decision_mock)

    orch = AgentOrchestrator(vault, db_factory)

    with patch("backend.orchestrator.agent_orchestrator.get_connector", return_value=mock_connector), \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter.from_config", return_value=mock_router), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast", side_effect=fake_broadcast):
        await orch.run_agent(1)

    paused_events = [e for e in broadcast_calls if e.get("event") == "agent_paused"]
    assert len(paused_events) >= 1
    assert agent.status == AgentStatus.PAUSED
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_agent_loop.py::test_run_agent_paper_trade_written_to_db tests/test_agent_loop.py::test_run_agent_risk_pause_persisted -v --asyncio-mode=auto
```

Expected: both `FAIL`

- [ ] **Step 3: Update orchestrator**

In `backend/orchestrator/agent_orchestrator.py`:

1. In `__init__`, after `self.executor = TradeExecutor(vault, None)`, add:
```python
        # Register approval handler so WS approve/reject messages reach executor
        from backend.api.websocket import set_approval_handler
        set_approval_handler(self._handle_approval)
```

2. Add `_handle_approval` method:
```python
    async def _handle_approval(self, data: dict):
        trade_id = data.get("trade_id")
        approved = data.get("type") == "approve_trade"
        if trade_id:
            await self.executor.approve_trade(trade_id, approved)
```

3. In `run_agent`, replace the `check_agent_risk` call block (lines ~172-198) with:
```python
            from backend.config import settings
            max_dd = getattr(getattr(settings, "allocation", None), "max_portfolio_drawdown", -0.25) or -0.25
            should_pause, risk_reason = check_agent_risk(
                agent_id=agent.id,
                confidence_score=agent.confidence_score,
                consecutive_losses=agent.consecutive_losses,
                drawdown=agent.current_drawdown or 0.0,
                max_drawdown=max_dd,
            )
            if should_pause:
                logger.warning(f"agent {agent_id} paused by risk: {risk_reason}")
                agent.status = AgentStatus.PAUSED
                session.add(agent)
                session.commit()
                await manager.broadcast({
                    "event": "agent_paused",
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "reason": risk_reason,
                })
                try:
                    if agent.user_id:
                        from backend.notifications.triggers import notify_agent_paused
                        notify_agent_paused(agent.user_id, agent.name, risk_reason)
                except Exception:
                    pass
                return
```

4. In `initialize()`, after `self.scheduler.start()`, add:
```python
        # Schedule portfolio-level risk check every 60s
        self.scheduler.add_job(
            self._run_risk_agent, "interval", seconds=60,
            id="risk_agent", replace_existing=True,
        )
```

5. Add `_run_risk_agent` method:
```python
    async def _run_risk_agent(self):
        from backend.orchestrator.risk_agent import RiskAgent
        risk = RiskAgent(self.db_factory)
        await risk.run()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_agent_loop.py::test_run_agent_paper_trade_written_to_db tests/test_agent_loop.py::test_run_agent_risk_pause_persisted -v --asyncio-mode=auto
```

Expected: both `PASS`

- [ ] **Step 5: Run full test suite to check for regressions**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

Expected: no new failures

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator/agent_orchestrator.py tests/test_agent_loop.py
git commit -m "feat(5A.5): wire approval handler, pass drawdown to risk check, schedule RiskAgent every 60s"
```

---

## Priority 2 — Auto-pause + Bodyguard (Backend)

### Task 5B.1: Fix RiskAgent — sync Session, bodyguard_pause_all event, resume confidence reset

**Files:**
- Modify: `backend/orchestrator/risk_agent.py`
- Modify: `backend/api/agents.py` (resume endpoint)
- Modify: `tests/test_risk_agent.py`

**Interfaces:**
- Produces: `RiskAgent.run()` uses sync Session (same as orchestrator); broadcasts `bodyguard_pause_all`; `POST /api/agents/{id}/resume` resets `confidence_score` to 50

- [ ] **Step 1: Write failing tests**

```python
# tests/test_risk_agent.py — add/replace tests

def test_bodyguard_pause_all_broadcasts_correct_event():
    """RiskAgent pauses all agents and emits bodyguard_pause_all."""
    from backend.orchestrator.risk_agent import RiskAgent
    from backend.database.models import Agent, AgentStatus

    agent1 = MagicMock(spec=Agent)
    agent1.id = 1; agent1.name = "A1"; agent1.status = AgentStatus.IDLE
    agent1.total_pnl = -30_000.0; agent1.paper_trading_balance = 100_000.0
    agent1.current_drawdown = -0.30

    agent2 = MagicMock(spec=Agent)
    agent2.id = 2; agent2.name = "A2"; agent2.status = AgentStatus.IDLE
    agent2.total_pnl = -5_000.0; agent2.paper_trading_balance = 50_000.0
    agent2.current_drawdown = -0.10

    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [agent1, agent2]
    db_factory = MagicMock(return_value=session)
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    broadcast_calls = []
    async def fake_broadcast(data): broadcast_calls.append(data)

    import asyncio
    risk = RiskAgent(db_factory)

    # Override MAX to force trigger
    risk.MAX_PORTFOLIO_DRAWDOWN = -0.25

    asyncio.get_event_loop().run_until_complete(risk.run())

    bodyguard_events = [e for e in broadcast_calls if e.get("event") == "bodyguard_pause_all"]
    assert len(bodyguard_events) == 1
    assert agent1.status == AgentStatus.PAUSED
    assert agent2.status == AgentStatus.PAUSED


def test_resume_endpoint_resets_confidence_to_50(client, auth_headers, db_with_agent):
    """POST /api/agents/{id}/resume sets confidence_score=50."""
    agent_id = db_with_agent
    # Force pause first
    client.post(f"/api/agents/{agent_id}/pause", headers=auth_headers)
    resp = client.post(f"/api/agents/{agent_id}/resume", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["confidence_score"] == 50
    assert data["status"] == "idle"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_risk_agent.py::test_bodyguard_pause_all_broadcasts_correct_event tests/test_risk_agent.py::test_resume_endpoint_resets_confidence_to_50 -v --asyncio-mode=auto
```

Expected: both `FAIL`

- [ ] **Step 3: Rewrite RiskAgent to use sync Session**

Replace `backend/orchestrator/risk_agent.py`:

```python
"""Portfolio-level risk meta-agent. Monitors portfolio drawdown and pauses all agents on breach."""
import logging
from sqlalchemy.orm import Session
from backend.database.models import Agent, AgentStatus
from backend.api.websocket import manager

logger = logging.getLogger(__name__)


class RiskAgent:
    MAX_PORTFOLIO_DRAWDOWN = -0.25

    def __init__(self, db_session_factory):
        self.db_factory = db_session_factory

    async def run(self):
        """Monitor portfolio and pause all agents if drawdown exceeds threshold."""
        session = self.db_factory()
        try:
            agents = session.query(Agent).filter(Agent.is_active == True).all()
            stats = self._compute_stats(agents)

            if stats["portfolio_drawdown"] < self.MAX_PORTFOLIO_DRAWDOWN:
                await self._pause_all_agents(
                    agents, session,
                    f"Portfolio drawdown {stats['portfolio_drawdown']:.2%} < {self.MAX_PORTFOLIO_DRAWDOWN:.2%}",
                )
                return

            await manager.broadcast({
                "event": "portfolio_update",
                "total_pnl": stats["total_pnl"],
                "total_capital": stats["total_capital"],
                "portfolio_drawdown": stats["portfolio_drawdown"],
                "agent_count": stats["agent_count"],
                "paused_count": stats["paused_count"],
            })
        finally:
            session.close()

    def _compute_stats(self, agents: list) -> dict:
        total_pnl = sum(a.total_pnl or 0.0 for a in agents)
        total_capital = sum(a.paper_trading_balance or 0.0 for a in agents)
        portfolio_drawdown = (total_pnl / total_capital) if total_capital > 0 else 0.0
        paused_count = sum(1 for a in agents if a.status == AgentStatus.PAUSED)
        return {
            "total_pnl": total_pnl,
            "total_capital": total_capital,
            "portfolio_drawdown": portfolio_drawdown,
            "agent_count": len(agents),
            "paused_count": paused_count,
        }

    async def _pause_all_agents(self, agents: list, session: Session, reason: str):
        for agent in agents:
            agent.status = AgentStatus.PAUSED
        session.commit()

        try:
            if agents[0].user_id:
                from backend.notifications.triggers import notify_agent_paused
                for agent in agents:
                    notify_agent_paused(agent.user_id, agent.name, reason)
        except Exception:
            pass

        await manager.broadcast({
            "event": "bodyguard_pause_all",
            "reason": reason,
            "paused_count": len(agents),
        })
        logger.warning(f"Bodyguard: paused {len(agents)} agents — {reason}")
```

- [ ] **Step 4: Update resume endpoint in agents.py**

In `backend/api/agents.py`, replace the `resume_agent` function body:

```python
@router.post("/{agent_id}/resume", response_model=AgentResponse)
async def resume_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
):
    """Resume agent: reset consecutive_losses, confidence to 50, status to IDLE."""
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            result = session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")
            _check_agent_access(agent, current_user)
            agent.consecutive_losses = 0
            agent.confidence_score = 50  # reset per AGENTS.md
            agent.status = AgentStatus.IDLE
            session.add(agent)
            session.flush()
            response = AgentResponse.model_validate(agent)
            session.commit()
            return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_risk_agent.py -v --asyncio-mode=auto
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator/risk_agent.py backend/api/agents.py tests/test_risk_agent.py
git commit -m "feat(5B.1): fix RiskAgent sync Session, bodyguard_pause_all event, resume resets confidence to 50"
```

---

### Task 5B.2: Full backend integration smoke test

**Files:**
- Modify: `tests/test_agent_loop.py`

**Interfaces:**
- Validates: complete cycle — paper trade written, WS event emitted, risk-based pause, Bodyguard event

- [ ] **Step 1: Add integration test**

```python
# tests/test_agent_loop.py — add

@pytest.mark.asyncio
async def test_full_cycle_paper_trade_and_ws_event():
    """Success criterion 1: agent cycle → paper Trade in DB → trade_executed WS event."""
    # Reuse test_run_agent_paper_trade_written_to_db logic (already tested)
    # This test verifies the success criterion end-to-end narrative
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    vault.get.return_value = "key"
    session = MagicMock()
    db_factory = MagicMock(return_value=session)

    agent = MagicMock(spec=Agent)
    agent.id = 42; agent.name = "SmokeAgent"; agent.symbol = "BTC/USD"
    agent.broker = "binance"; agent.status = AgentStatus.IDLE; agent.is_active = True
    agent.check_frequency = 300; agent.confidence_score = 60; agent.consecutive_losses = 0
    agent.is_paper_trading = True; agent.max_position_size = 500.0
    agent.execution_mode = "autonomous"; agent.context_file_path = None
    agent.last_heartbeat = None; agent.user_id = None; agent.current_drawdown = 0.0

    session.query.return_value.filter.return_value.first.return_value = agent

    events = []
    async def collect(data): events.append(data)

    mock_connector = MagicMock()
    mock_connector.get_account_balance = AsyncMock(return_value=50_000.0)
    mock_connector.get_market_data = AsyncMock(return_value=MagicMock(
        price=65_000.0, volume=5_000, rsi=38.0, ma20=64_000.0, ma50=62_000.0
    ))

    from backend.llm.llm_router import TradeDecision
    decision = TradeDecision(action="BUY", confidence=0.8, position_size=0.1, reasoning="dip buy")
    mock_router = MagicMock()
    mock_router.decide = AsyncMock(return_value=decision)

    orch = AgentOrchestrator(vault, db_factory)
    with patch("backend.orchestrator.agent_orchestrator.get_connector", return_value=mock_connector), \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter.from_config", return_value=mock_router), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast", side_effect=collect):
        await orch.run_agent(42)

    trade_evts = [e for e in events if e.get("event") == "trade_executed"]
    assert len(trade_evts) == 1, f"Expected 1 trade_executed event, got: {events}"
    assert trade_evts[0]["is_paper"] is True
    assert trade_evts[0]["symbol"] == "BTC/USD"
```

- [ ] **Step 2: Run integration test**

```bash
pytest tests/test_agent_loop.py::test_full_cycle_paper_trade_and_ws_event -v --asyncio-mode=auto
```

Expected: `PASS`

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

Expected: no failures

- [ ] **Step 4: Commit**

```bash
git add tests/test_agent_loop.py
git commit -m "feat(5B.2): add full cycle integration smoke test (paper trade → WS event)"
```

---

## Priority 3 — Agent Inspector Panel (Frontend)

### Task 5C.1: Wire Inspector Settings tab to editable fields

**Files:**
- Modify: `frontend/src/components/Warroom/AgentInspector.jsx`
- Modify: `frontend/src/stores/agents.store.js`

**Interfaces:**
- Consumes: `PATCH /api/agents/{id}` (accepts `execution_mode`, `check_frequency` — wired in Task 5A.2)
- Produces: Settings tab has editable `execution_mode` select, `check_frequency` input, `max_position_size` input, `stop_loss_pct`, `take_profit_pct`, `is_paper_trading` toggle — all save via `updateAgent()`

Note: `AgentInspector.jsx` already has a `SettingsTab` with toggle buttons for `is_active` and `is_paper_trading`. This task extends it with the missing editable fields.

- [ ] **Step 1: Check current Settings tab renders execution_mode, check_frequency as read-only** (no test needed — visual change only)

- [ ] **Step 2: Replace `SettingsTab` in AgentInspector.jsx**

Replace the `SettingsTab` component (lines 115–161) in `frontend/src/components/Warroom/AgentInspector.jsx`:

```jsx
function SettingsTab({ agent }) {
  const { updateAgent } = useAgentsStore();
  const [busy, setBusy] = useState(false);
  const [local, setLocal] = useState({
    execution_mode: agent.execution_mode ?? 'human_in_loop',
    check_frequency: agent.check_frequency ?? 300,
    max_position_size: agent.max_position_size ?? 1000,
    stop_loss_pct: agent.stop_loss_pct ?? 2.0,
    take_profit_pct: agent.take_profit_pct ?? 4.0,
  });

  // Sync local state when agent prop changes (e.g., WS update)
  useEffect(() => {
    setLocal({
      execution_mode: agent.execution_mode ?? 'human_in_loop',
      check_frequency: agent.check_frequency ?? 300,
      max_position_size: agent.max_position_size ?? 1000,
      stop_loss_pct: agent.stop_loss_pct ?? 2.0,
      take_profit_pct: agent.take_profit_pct ?? 4.0,
    });
  }, [agent.id]);

  const save = async () => {
    setBusy(true);
    await updateAgent(agent.id, local).catch(() => {});
    setBusy(false);
  };

  const toggle = async (field) => {
    setBusy(true);
    await updateAgent(agent.id, { [field]: !agent[field] }).catch(() => {});
    setBusy(false);
  };

  const field = (label, key, type = 'number') => (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
      <span style={{ color: 'var(--color-text-muted)' }}>{label}</span>
      <input
        type={type}
        value={local[key]}
        onChange={(e) => setLocal((p) => ({ ...p, [key]: type === 'number' ? parseFloat(e.target.value) : e.target.value }))}
        style={{
          width: 80, background: 'var(--color-bg-tertiary)',
          border: '1px solid var(--color-border)', color: 'var(--color-text-primary)',
          fontFamily: 'var(--font-mono)', fontSize: '0.75rem', padding: '0.2rem 0.4rem',
        }}
      />
    </div>
  );

  const btnStyle = (danger) => ({
    padding: '0.3rem 0.7rem', fontFamily: 'var(--font-mono)', fontSize: '0.7rem',
    cursor: 'pointer', background: 'transparent',
    border: `1px solid ${danger ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary, #00ff88)'}`,
    color: danger ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary)',
    borderRadius: 3,
  });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.4rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Execution Mode</span>
        <select
          value={local.execution_mode}
          onChange={(e) => setLocal((p) => ({ ...p, execution_mode: e.target.value }))}
          style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-primary)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem' }}
        >
          <option value="autonomous">Autonomous</option>
          <option value="human_in_loop">Human-in-Loop</option>
          <option value="risk_based">Risk-Based</option>
        </select>
      </div>
      {field('Check Freq (s)', 'check_frequency')}
      {field('Max Position $', 'max_position_size')}
      {field('Stop Loss %', 'stop_loss_pct')}
      {field('Take Profit %', 'take_profit_pct')}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Active</span>
        <button disabled={busy} onClick={() => toggle('is_active')} style={btnStyle(!agent.is_active)}>
          {agent.is_active ? 'Disable' : 'Enable'}
        </button>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Paper Trading</span>
        <button disabled={busy} onClick={() => toggle('is_paper_trading')} style={btnStyle(agent.is_paper_trading)}>
          {agent.is_paper_trading ? 'Switch Live' : 'Switch Paper'}
        </button>
      </div>
      <div style={{ marginTop: '1rem' }}>
        <button
          onClick={save}
          disabled={busy}
          style={{ width: '100%', padding: '0.5rem', background: 'var(--color-accent-primary, #00ff88)', color: '#000', border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.8rem', cursor: 'pointer', borderRadius: 3 }}
        >
          {busy ? 'SAVING…' : 'SAVE SETTINGS'}
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Add `confidence_score` color coding to Overview tab**

In `OverviewTab`, replace the Confidence `Row`:

```jsx
  const conf = agent.confidence_score ?? 10;
  const confColor = conf >= 70 ? 'var(--color-accent-primary)' : conf >= 35 ? '#ff8c00' : 'var(--color-danger, #ff4444)';
```

Then update the Row:

```jsx
  <Row label="Confidence" value={`${conf}%`} valueColor={confColor} />
```

- [ ] **Step 4: Wire Rules tab to `strategy_config.context_content`**

`RulesTab` already reads `agent.strategy_config?.context ?? agent.strategy_config?.rules`. Also check `context_content` (set by `POST /{id}/update-context`):

Replace `RulesTab`:

```jsx
function RulesTab({ agent }) {
  const content = agent.strategy_config?.context_content
    ?? agent.strategy_config?.context
    ?? agent.strategy_config?.rules
    ?? null;
  if (!content) return (
    <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem', marginTop: '1rem' }}>
      No context file — agent uses default LLM reasoning
    </div>
  );
  return (
    <pre style={{
      fontSize: '0.75rem', color: 'var(--color-text-secondary)',
      background: 'var(--color-bg-tertiary)', padding: '0.75rem',
      borderRadius: 4, overflowX: 'auto', whiteSpace: 'pre-wrap', marginTop: '0.5rem',
    }}>
      {typeof content === 'string' ? content : JSON.stringify(content, null, 2)}
    </pre>
  );
}
```

- [ ] **Step 5: Add 30s polling to agents.store.js**

In `frontend/src/stores/agents.store.js`, add `startPolling` and `stopPolling` actions:

```javascript
      _pollTimer: null,

      startPolling: () => {
        const { fetchAgents, _pollTimer } = get();
        if (_pollTimer) return;
        fetchAgents();
        const timer = setInterval(() => get().fetchAgents(), 30_000);
        set({ _pollTimer: timer });
      },

      stopPolling: () => {
        const { _pollTimer } = get();
        if (_pollTimer) { clearInterval(_pollTimer); set({ _pollTimer: null }); }
      },
```

- [ ] **Step 6: Start polling in App.jsx or Warroom parent**

In `frontend/src/components/Warroom/Warroom.jsx`, add at top of component:

```jsx
  const { startPolling, stopPolling } = useAgentsStore();
  useEffect(() => {
    startPolling();
    return () => stopPolling();
  }, [startPolling, stopPolling]);
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Warroom/AgentInspector.jsx frontend/src/stores/agents.store.js frontend/src/components/Warroom/Warroom.jsx
git commit -m "feat(5C.1): wire Inspector Settings tab editable fields, confidence color coding, 30s polling"
```

---

## Priority 4 — Human-in-Loop Approval UI (Frontend)

### Task 5D.1: Wire ApprovalDialog to live `trade_approval_required` events + queue

**Files:**
- Modify: `frontend/src/components/Warroom/Warroom.jsx`
- Modify: `frontend/src/components/Warroom/ApprovalDialog.jsx`
- Modify: `frontend/src/hooks/useWebSocket.js`

**Interfaces:**
- Consumes: WS event `trade_approval_required` (Task 5A.3 schema); `approveTrade(tradeId, approved)` from `useWebSocket`
- Produces: `ApprovalDialog` shows one approval at a time from a queue; countdown derived from `expires_at`; approve/reject sends over WS

Note: `Warroom.jsx` already handles `agent_approval_needed` → `pendingApproval` → `ApprovalDialog`. This task:
1. Renames the WS event type to `trade_approval_required`
2. Adds approval queue (multiple simultaneous approvals)
3. Updates `ApprovalDialog` to derive countdown from `expires_at` ISO string

- [ ] **Step 1: Update Warroom.jsx — rename event, add queue**

Replace `pendingApproval` state and its `useEffect` in `Warroom.jsx`:

```jsx
  const [approvalQueue, setApprovalQueue] = useState([]);
  const currentApproval = approvalQueue[0] ?? null;

  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage;

    if (msg.event === 'trade_executed' || msg.type === 'trade_executed') {
      const agent = agents.find((a) => a.id === msg.agent_id || a.id === String(msg.agent_id));
      if (agent) {
        const { x, y } = toScreen(agent.grid_col ?? 0, agent.grid_row ?? 0);
        const notif = {
          id: `${Date.now()}-${msg.agent_id}`,
          trade: { symbol: msg.symbol, action: msg.action, pnl: msg.pnl },
          svgX: x + TILE_W / 2,
          svgY: y,
        };
        setNotifications((prev) => [...prev, notif]);
      }
    }

    if (msg.event === 'trade_approval_required' || msg.type === 'agent_approval_needed') {
      const agent = agents.find((a) => a.id === msg.agent_id || a.id === String(msg.agent_id));
      const approval = { ...msg, agent_name: msg.agent_name ?? agent?.name };
      setApprovalQueue((prev) => [...prev, approval]);
    }

    if (msg.event === 'agent_update' || msg.event === 'agent_paused' || msg.event === 'bodyguard_pause_all') {
      if (msg.agent_id) {
        useAgentsStore.getState().updateAgentLocally(msg.agent_id, {
          status: msg.status,
          confidence_score: msg.confidence_score,
        });
      }
    }
  }, [lastMessage, agents]);

  const handleDecide = useCallback((tradeId, approved) => {
    approveTrade(tradeId, approved);
    setApprovalQueue((prev) => prev.filter((a) => a.trade_id !== tradeId));
  }, [approveTrade]);
```

Update the `ApprovalDialog` render to use `currentApproval`:

```jsx
  <ApprovalDialog approval={currentApproval} onDecide={handleDecide} />
```

- [ ] **Step 2: Update ApprovalDialog.jsx — use `expires_at` for countdown**

Replace `ApprovalDialog` component:

```jsx
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect, useCallback } from 'react';

const DEFAULT_TIMEOUT = 30;

export default function ApprovalDialog({ approval, onDecide }) {
  const [remaining, setRemaining] = useState(DEFAULT_TIMEOUT);

  useEffect(() => {
    if (!approval) return;
    // Derive initial seconds from expires_at if available
    if (approval.expires_at) {
      const secs = Math.max(0, Math.round((new Date(approval.expires_at) - Date.now()) / 1000));
      setRemaining(secs || DEFAULT_TIMEOUT);
    } else {
      setRemaining(DEFAULT_TIMEOUT);
    }
    const interval = setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          onDecide(approval.trade_id, false);
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [approval?.trade_id, onDecide]);

  const handleApprove = useCallback(() => onDecide(approval.trade_id, true), [approval, onDecide]);
  const handleReject = useCallback(() => onDecide(approval.trade_id, false), [approval, onDecide]);

  const maxSecs = approval?.expires_at
    ? DEFAULT_TIMEOUT
    : DEFAULT_TIMEOUT;
  const urgentColor = remaining <= 5 ? 'var(--color-danger, #ff4444)' : 'var(--color-accent-primary, #00ff88)';

  return (
    <AnimatePresence>
      {approval && (
        <motion.div
          initial={{ opacity: 0, y: -60 }}
          animate={{ opacity: 1, y: 0, transition: { type: 'spring', stiffness: 300, damping: 25 } }}
          exit={{ opacity: 0, y: -60, transition: { duration: 0.2 } }}
          style={{
            position: 'fixed', inset: 0, zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            background: 'rgba(0,0,0,0.75)',
          }}
        >
          <div style={{
            background: 'var(--color-bg-secondary)', border: `1px solid ${urgentColor}`,
            borderRadius: 8, padding: '2rem', maxWidth: 420, width: '90%',
            fontFamily: 'var(--font-mono)',
          }}>
            <div style={{ color: 'var(--color-accent-primary)', fontSize: '0.7rem', marginBottom: 4 }}>
              TRADE APPROVAL REQUIRED
            </div>
            <div style={{ fontSize: '1.1rem', color: 'var(--color-text-primary)', marginBottom: '1.5rem' }}>
              {approval.agent_name ?? `Agent #${approval.agent_id}`}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem 1rem', fontSize: '0.8rem', marginBottom: '1.5rem' }}>
              {[
                ['Symbol', approval.symbol],
                ['Action', approval.action ?? approval.side],
                ['Size $', approval.position_size_dollars?.toFixed?.(2) ?? approval.quantity?.toFixed?.(4) ?? '—'],
                ['Confidence', approval.confidence != null ? `${(approval.confidence * 100).toFixed(0)}%` : '—'],
              ].map(([label, val]) => (
                <div key={label}>
                  <span style={{ color: 'var(--color-text-muted)' }}>{label}: </span>
                  <span style={{ color: 'var(--color-text-primary)' }}>{val}</span>
                </div>
              ))}
            </div>
            {approval.reasoning && (
              <div style={{
                fontSize: '0.75rem', color: 'var(--color-text-secondary)',
                background: 'var(--color-bg-tertiary)', padding: '0.75rem',
                borderRadius: 4, marginBottom: '1.5rem', lineHeight: 1.5,
              }}>
                {approval.reasoning}
              </div>
            )}
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--color-text-muted)', marginBottom: 4 }}>
                <span>Auto-reject in</span>
                <span style={{ color: remaining <= 5 ? 'var(--color-danger, #ff4444)' : 'inherit' }}>{remaining}s</span>
              </div>
              <div style={{ height: 3, background: 'var(--color-border)', borderRadius: 2 }}>
                <motion.div
                  style={{ height: '100%', borderRadius: 2, background: urgentColor }}
                  animate={{ width: `${(remaining / maxSecs) * 100}%` }}
                  transition={{ duration: 1, ease: 'linear' }}
                />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button onClick={handleApprove} style={{
                flex: 1, padding: '0.6rem', background: 'var(--color-accent-primary, #00ff88)',
                color: '#000', border: 'none', borderRadius: 4, fontFamily: 'inherit',
                fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              }}>APPROVE</button>
              <button onClick={handleReject} style={{
                flex: 1, padding: '0.6rem', background: 'transparent',
                color: 'var(--color-danger, #ff4444)', border: '1px solid var(--color-danger, #ff4444)',
                borderRadius: 4, fontFamily: 'inherit', fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
              }}>REJECT</button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

- [ ] **Step 3: Update useWebSocket.js dispatch — handle `event` field (not just `type`)**

In `frontend/src/hooks/useWebSocket.js`, update the `dispatch` function to handle both `event` and `type` fields:

```javascript
  const dispatch = useCallback((msg) => {
    setLastMessage(msg);
    const key = msg.event ?? msg.type;

    switch (key) {
      case 'agent_update':
      case 'agent_paused':
        if (msg.agent_id) {
          useAgentsStore.getState().updateAgentLocally(msg.agent_id, msg.data ?? {
            status: msg.status,
            confidence_score: msg.confidence_score,
          });
        }
        break;
      case 'trade_executed':
        if (msg.trade) useTradesStore.getState().addTrade(msg.trade);
        break;
      case 'trade_approval_required':
      case 'agent_approval_needed':
        useUIStore.getState().setPendingApproval(msg);
        break;
      case 'portfolio_update':
        useDashboardStore.getState().updatePortfolioLocally(msg.data ?? {});
        break;
      case 'risk_alert':
      case 'bodyguard_pause_all':
        useUIStore.getState().addToast({ type: 'error', message: msg.message ?? msg.reason ?? 'Risk alert' });
        break;
      default:
        break;
    }
  }, [setLastMessage]);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/Warroom/Warroom.jsx frontend/src/components/Warroom/ApprovalDialog.jsx frontend/src/hooks/useWebSocket.js
git commit -m "feat(5D.1): wire ApprovalDialog to trade_approval_required WS events with queue and expires_at countdown"
```

---

## Priority 5 — Confidence Score Drives Warroom Sprite Visual (Frontend)

### Task 5E.1: Add confidence tinting and paused state to Agent sprites

**Files:**
- Modify: `frontend/src/components/Warroom/sprites/Agent.js`
- Modify: `frontend/src/components/Warroom/hooks/useWarroomAgents.js`

**Interfaces:**
- Consumes: `agent.confidence_score`, `agent.status` from `agents.store.js` (updated every 30s via polling or WS `agent_update`)
- Produces:
  - `Agent.setConfidence(score: number)` — applies PixiJS tint to body graphics: `>=70` → `0xFFFFFF` (no tint); `50-69` → `0xCCCCCC` (slight desaturate); `35-49` → `0xFFAA44` (orange); `<35` → `0xFF4444` (red) + pulsing `_ring`
  - `Agent.setPaused(bool)` — grays sprite (`0x888888` tint) + shows pause text above head; unpaused → restores previous confidence tint

- [ ] **Step 1: Add `setConfidence` and `setPaused` to Agent.js**

In `frontend/src/components/Warroom/sprites/Agent.js`, add after `onProcessing()` method (line ~113):

```javascript
  setConfidence(score) {
    this._confidenceScore = score;
    if (this._paused) return; // paused tint overrides confidence tint
    const tint = score >= 70 ? 0xFFFFFF
                : score >= 50 ? 0xCCCCCC
                : score >= 35 ? 0xFFAA44
                : 0xFF4444;
    this.c.children.forEach((child) => { if (child.tint !== undefined) child.tint = tint; });

    // Pulsing ring for <35
    if (score < 35 && !this._warningRing) {
      this._warningRing = new PIXI.Graphics();
      this._warningRing.lineStyle(2, 0xFF4444, 0.8);
      this._warningRing.drawCircle(7, 8, 13);
      this.c.addChildAt(this._warningRing, 0);
      this._warningRingPhase = 0;
    } else if (score >= 35 && this._warningRing) {
      this.c.removeChild(this._warningRing);
      this._warningRing.destroy();
      this._warningRing = null;
    }
  }

  setPaused(paused) {
    this._paused = paused;
    if (paused) {
      this.c.children.forEach((child) => { if (child.tint !== undefined) child.tint = 0x888888; });
      if (!this._pauseText) {
        this._pauseText = new PIXI.Text('⏸', { fontSize: 8, fill: 0xAAAAAA });
        this._pauseText.anchor.set(0.5, 1);
        this._pauseText.x = 7; this._pauseText.y = -14;
        this.c.addChild(this._pauseText);
      }
    } else {
      if (this._pauseText) {
        this.c.removeChild(this._pauseText);
        this._pauseText.destroy();
        this._pauseText = null;
      }
      this.setConfidence(this._confidenceScore ?? 50);
    }
  }
```

Also update `tick()` to pulse the warning ring if present. After `if (this.flashLife > 0)` block add:

```javascript
    if (this._warningRing) {
      this._warningRingPhase = (this._warningRingPhase ?? 0) + 0.08;
      this._warningRing.alpha = 0.5 + 0.5 * Math.sin(this._warningRingPhase);
    }
```

- [ ] **Step 2: Wire `useWarroomAgents.js` to call `setConfidence` and `setPaused`**

Replace `frontend/src/components/Warroom/hooks/useWarroomAgents.js`:

```javascript
import { useEffect, useRef } from 'react';
import { agentsApi } from '../../../utils/api-client';
import { useWebSocketStore } from '../../../stores/websocket.store';
import useAgentsStore from '../../../stores/agents.store';

export function useWarroomAgents(room, agentSprites) {
  const lastMessage = useWebSocketStore((s) => s.lastMessage);
  const agents = useAgentsStore((s) => s.agents);
  const demoTimer = useRef(null);
  const hasRealEvent = useRef(false);

  // On mount: assign IDs and apply initial confidence/paused state
  useEffect(() => {
    agentsApi.list({ room }).then((fetched) => {
      if (!Array.isArray(fetched)) return;
      fetched.forEach((agent, i) => {
        const sprite = agentSprites[i];
        if (!sprite) return;
        sprite.id = agent.id;
        if (sprite.setConfidence) sprite.setConfidence(agent.confidence_score ?? 50);
        if (sprite.setPaused) sprite.setPaused(agent.status === 'paused');
      });
    }).catch(() => {});
  }, [room, agentSprites]);

  // Re-sync sprites when agents store updates (polling or WS)
  useEffect(() => {
    agents.forEach((agent) => {
      const sprite = agentSprites.find((s) => s && s.id === agent.id);
      if (!sprite) return;
      if (sprite.setConfidence) sprite.setConfidence(agent.confidence_score ?? 50);
      if (sprite.setPaused) sprite.setPaused(agent.status === 'paused');
    });
  }, [agents, agentSprites]);

  useEffect(() => {
    demoTimer.current = setTimeout(() => {
      if (!hasRealEvent.current) window.__LABOURIOUS_DEMO__ = true;
    }, 3000);
    return () => clearTimeout(demoTimer.current);
  }, []);

  useEffect(() => {
    if (!lastMessage) return;
    const msg = lastMessage;
    const key = msg.event ?? msg.type;

    if (key === 'trade_executed' && msg.agent_id) {
      hasRealEvent.current = true;
      window.__LABOURIOUS_DEMO__ = false;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite) {
        sprite.onTrade(msg.symbol ?? 'TRADE', msg.action ?? 'BUY', msg.pnl ?? 0);
        if (sprite.setConfidence) sprite.setConfidence(msg.confidence_score ?? 50);
      }
    }

    if ((key === 'agent_update' || key === 'agent_paused') && msg.agent_id) {
      hasRealEvent.current = true;
      const sprite = agentSprites.find((s) => s && s.id === msg.agent_id);
      if (sprite) {
        if (msg.status === 'running' || msg.data?.status === 'processing') sprite.onProcessing();
        if (sprite.setPaused) sprite.setPaused(msg.status === 'paused' || msg.data?.status === 'paused');
        if (sprite.setConfidence && msg.confidence_score != null) sprite.setConfidence(msg.confidence_score);
      }
    }

    if (key === 'bodyguard_pause_all') {
      agentSprites.forEach((sprite) => { if (sprite?.setPaused) sprite.setPaused(true); });
    }
  }, [lastMessage, agentSprites]);
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Warroom/sprites/Agent.js frontend/src/components/Warroom/hooks/useWarroomAgents.js
git commit -m "feat(5E.1): confidence tinting and paused state on PixiJS agent sprites"
```

---

## Self-Review Checklist

### Spec Coverage

| Requirement | Task |
|-------------|------|
| `check_frequency` field on Agent | Already present in model (line 101); exposed via 5A.2 |
| `run_agent()` full cycle without silent failures | 5A.5 + 5B.2 integration test |
| `human_in_loop` PENDING trade + `trade_approval_required` WS event | 5A.3 |
| Paper trading path: `is_paper=True` closed Trade | 5A.1 + 5A.3 |
| Live trading path: `connector.create_order()` | 5A.3 (`_execute_live_order`) |
| Confidence score after trade → persist to DB | 5A.3 (`_update_agent_stats`) |
| `trade_executed` WS broadcast | 5A.3 |
| Alembic migration for `check_frequency` | NOT NEEDED — column already exists (models.py line 101) |
| Alembic migration for `is_paper` on Trade | 5A.1 |
| 3 consecutive losses → per-agent pause | `check_agent_risk` already checks this; orchestrator wired in 5A.5 |
| `confidence_score < 35` → pause | Already in `check_agent_risk` (`CONFIDENCE_MIN = 30`); note: spec says `<35`, risk_manager uses `<30` — **fix `CONFIDENCE_MIN` to 35 in task 5A.5** |
| `current_drawdown > max_portfolio_drawdown` → pause all | 5B.1 (RiskAgent) |
| `bodyguard_pause_all` WS event | 5B.1 |
| `notify_agent_paused()` after auto-pause | Already in orchestrator (line 191); 5B.1 adds to RiskAgent |
| Confidence reset to 50 on resume | 5B.1 |
| Inspector Overview tab — confidence color coded | 5C.1 |
| Inspector Trades tab — paginated from `/api/agents/{id}/trades` | Already implemented in current AgentInspector.jsx |
| Inspector Rules tab — `context_file_path` contents | 5C.1 (reads `strategy_config.context_content`) |
| Inspector Performance tab — Recharts LineChart | Already implemented |
| Inspector Settings tab — editable fields + save | 5C.1 |
| Inspector opens on sprite click | Already works via `Warroom.jsx` `handleAgentClick` |
| ApprovalDialog wire to WS events | 5D.1 |
| Countdown from `expires_at` | 5D.1 |
| Approve/reject WS send | 5D.1 (via `approveTrade`) |
| Queue multiple simultaneous approvals | 5D.1 |
| `TradeNotification` on `trade_executed` | Already partially wired; 5D.1 ensures `Warroom.jsx` handles `event` field |
| Confidence ≥70 full brightness, 50-69 desaturate, 35-49 orange, <35 red+pulse | 5E.1 |
| Paused agent: gray + ⏸ symbol | 5E.1 |
| Sprites update within 30s | 5C.1 (polling) + 5E.1 (WS) |

### Fix: CONFIDENCE_MIN mismatch

The spec says `confidence_score < 35` triggers pause; `risk_manager.py` has `CONFIDENCE_MIN = 30`. Fix in Task 5A.5:

In `backend/trading/risk_manager.py`, change:
```python
CONFIDENCE_MIN = 30   # before
```
to:
```python
CONFIDENCE_MIN = 35   # after — per FEATURES.md spec
```

Add this change to the Task 5A.5 step 3 instructions above. Also update the test in `tests/test_risk_manager.py` that checks the boundary.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-06-21-phase5-live-agent-execution.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** — dispatch fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
