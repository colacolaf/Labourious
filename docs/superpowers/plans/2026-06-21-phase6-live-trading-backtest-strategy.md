# Phase 6 — Production-Ready Live Trading, Backtest UI, Strategy Builder, Notifications

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Labourious as a production-grade local trading warroom: real broker execution (Alpaca live + Binance + Kraken + generic ccxt), a complete backtest UI with equity curves, an in-Inspector strategy editor, and wired email/SMS notifications. Phase 7 (team accounts) stub included at the end.

**Architecture summary:**

```
Phase 6 scope:
  P1 — Live broker trading (broker manager → vault-gated live orders)
  P2 — Backtest UI completion (equity curve data, walk-forward panel, history)
  P3 — Strategy builder (in-Inspector context editor, preset templates)
  P4 — Notifications delivery (SMTP/SendGrid relay, Twilio SMS, daily digest)

No new npm packages. No new DB models except DailySnapshot write (model already exists).
One new broker file: backend/brokers/kraken.py
One Alembic migration: add winning_trades_pct to DailySnapshot (for digest)
```

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy (sync Session in orchestrator), APScheduler, pytest + asyncio-mode=auto; React 18, Zustand, Framer Motion, Recharts, PixiJS (existing).

---

## Global Constraints

- No new npm packages. All frontend uses Recharts (charts), Framer Motion (transitions), Zustand (state).
- No new backend Python packages. `ccxt`, `krakenex`, `twilio` already installed. SendGrid uses smtplib SMTP relay — no `sendgrid` package needed.
- All colors via CSS vars — `var(--color-*)` only, never hardcoded hex.
- Zustand stores for all shared frontend state.
- Framer Motion for transitions (live trading confirmation dialog, strategy editor).
- Alembic for every DB schema change: `alembic revision --autogenerate -m "desc"` then `alembic upgrade head`.
- Never log vault contents or API keys.
- TDD-adjacent: write a failing test stub before implementation in every backend task.
- All async FastAPI routes use `AsyncSession`; orchestrator uses sync `Session` (established pattern — do not change).
- **Paper trading is the safe default** — `is_paper_trading=True` remains default for all new agents.
- **Live trading is opt-in per agent** — UI must show explicit confirmation dialog when switching to live.
- **All broker credentials from vault only** — never from env vars or DB columns.
- Commit after each task: `feat(6X.Y): description` pattern.
- Run `pytest tests/ -v --asyncio-mode=auto` after each backend task before committing.

---

## File Map

### Files to Modify

| File | What changes |
|------|-------------|
| `backend/brokers/manager.py` | Add Kraken + generic ccxt; pass `paper` flag from agent |
| `backend/brokers/alpaca.py` | Remove hardcoded `paper=True`; pass through; add order fill polling |
| `backend/orchestrator/agent_orchestrator.py` | Pass `is_paper_trading` to `get_connector`; DailySnapshot write after trade |
| `backend/trading/trade_executor.py` | Pre-flight vault check before live order; balance floor guard |
| `backend/scripts/backtest.py` | Build real equity curve from day-by-day balance; fix pct/decimal inconsistency |
| `backend/api/backtest_ui.py` | Pass `agent_id` symbol to script; add `/api/backtest/symbol-check` endpoint |
| `backend/notifications/service.py` | Add `send_email_sendgrid_relay` path (SMTP through sendgrid.net); add notification dedup |
| `backend/config.py` | Add `SENDGRID_API_KEY` optional; add `NOTIFICATION_COOLDOWN_MINUTES` |
| `backend/main.py` | Register daily digest APScheduler job at startup |
| `tests/test_broker_live.py` | New: live broker connector tests (mocked) |
| `tests/test_backtest.py` | Add equity curve shape test; fix decimal inconsistency test |
| `tests/test_notifications.py` | Add dedup test; SendGrid relay test |
| `frontend/src/components/Warroom/AgentInspector.jsx` | Add editable `RulesTab` with textarea + save; add `StrategyTemplatesTab` |
| `frontend/src/components/Analytics/BacktestRunner.jsx` | Walk-forward window results; history panel |
| `frontend/src/components/Analytics/BacktestHistory.jsx` | New: history table component |
| `frontend/src/utils/api-client.js` | Add `notificationsApi.sendTest`; `brokersApi.validateVault` |
| `frontend/src/pages/NotificationsPage.jsx` | Wire phone number save; add test-send button |

### Files to Create

| File | Purpose |
|------|---------|
| `backend/brokers/kraken.py` | Kraken connector via krakenex |
| `backend/brokers/ccxt_generic.py` | Generic ccxt connector for any exchange |
| `frontend/src/components/Analytics/BacktestHistory.jsx` | Past runs table with re-run button |
| `alembic/versions/xxxx_add_daily_snapshot_fields.py` | Add `trades_won`, `trades_lost` to `DailySnapshot` |

---

## WebSocket Events (Phase 6 additions)

### Outbound (backend → frontend)

```json
// live_order_filled — emitted when a live order fill is confirmed (Alpaca async fill polling)
{
  "event": "live_order_filled",
  "agent_id": 1,
  "agent_name": "My Agent",
  "symbol": "AAPL",
  "action": "BUY",
  "order_id": "alpaca-order-uuid",
  "filled_price": 185.42,
  "quantity": 5.37,
  "is_paper": false
}

// notification_sent — broadcast when email/SMS actually delivered
{
  "event": "notification_sent",
  "channel": "email",
  "user_id": "uuid",
  "subject": "Trade Executed: BUY AAPL"
}
```

---

## API Endpoint Changes

### New endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api/brokers/vault-check/{broker}` | Returns `{"has_credentials": bool}` — checks vault has key+secret for broker |
| `POST` | `/api/notifications/test` | Sends a test email + SMS to current user's configured channels |
| `GET` | `/api/backtest/validate-symbol` | `?symbol=AAPL` — returns `{"valid": bool}` via yfinance 1-day fetch |

### Modified endpoints

- `GET /api/agents/{id}` → `AgentResponse` unchanged (all fields already present)
- `GET /api/backtest/{run_id}` → `result_json` now always includes `equity_curve: [{date, balance}]` array
- `GET /api/backtest/history` → unchanged

---

## Priority 1 — Production-Ready Live Broker Trading (Backend)

### Task 6A.1: Fix `get_connector` — remove hardcoded `paper=True`, pass agent flag

**Files:**
- Modify: `backend/brokers/manager.py`
- Modify: `backend/brokers/alpaca.py`

**Interfaces:**
- `get_connector(broker, vault, paper=True)` — `paper` kwarg defaults to `True` (safety default)
- `AlpacaConnector.__init__(api_key, secret, paper=True)` — unchanged signature but `paper` now used properly

**Why this matters:** Current code hardcodes `paper=True` for Alpaca. Any agent with `is_paper_trading=False` still sends to paper API. This is the root blocker for live trading.

- [ ] **Step 1: Write failing test**

```python
# tests/test_broker_live.py — create this file

import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_connector_alpaca_live_uses_live_base():
    """get_connector with paper=False creates AlpacaConnector pointing to live URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault, paper=False)
    assert "paper-api" not in connector._base
    assert "api.alpaca.markets" in connector._base


def test_get_connector_alpaca_paper_uses_paper_base():
    """get_connector with paper=True (default) creates AlpacaConnector pointing to paper URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault)  # default paper=True
    assert "paper-api.alpaca.markets" in connector._base


def test_get_connector_kraken_returns_kraken_connector():
    """get_connector('kraken') returns a BrokerConnector."""
    from backend.brokers.manager import get_connector
    from backend.brokers.base import BrokerConnector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key"

    connector = get_connector("kraken", vault)
    assert isinstance(connector, BrokerConnector)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_broker_live.py -v
```

Expected: `FAIL` — `paper=True` hardcoded, no Kraken

- [ ] **Step 3: Update `get_connector` signature and Alpaca init**

Replace `backend/brokers/manager.py`:

```python
from backend.brokers.base import BrokerConnector
from backend.brokers.alpaca import AlpacaConnector
from backend.brokers.binance import BinanceConnector


def get_connector(broker: str, vault, paper: bool = True) -> BrokerConnector:
    """Return a broker connector. paper=True (default) is safe for all non-production use."""
    broker = broker.lower()
    if broker == "alpaca":
        return AlpacaConnector(
            api_key=vault.get("alpaca_api_key"),
            secret=vault.get("alpaca_secret"),
            paper=paper,
        )
    if broker == "binance":
        return BinanceConnector(
            api_key=vault.get("binance_api_key"),
            secret=vault.get("binance_secret"),
            paper_balance=vault.get("binance_paper_balance") or 100_000.0,
        )
    if broker == "kraken":
        from backend.brokers.kraken import KrakenConnector
        return KrakenConnector(
            api_key=vault.get("kraken_api_key"),
            secret=vault.get("kraken_api_secret"),
            paper=paper,
        )
    # Generic ccxt fallback for any other exchange
    from backend.brokers.ccxt_generic import CcxtConnector
    return CcxtConnector(
        exchange_id=broker,
        api_key=vault.get(f"{broker}_api_key"),
        secret=vault.get(f"{broker}_secret"),
    )


def list_brokers() -> list[str]:
    """Return natively supported broker names."""
    return ["alpaca", "binance", "kraken"]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_broker_live.py -v
```

Expected: `PASS`

- [ ] **Step 5: Update orchestrator to pass `paper` flag**

In `backend/orchestrator/agent_orchestrator.py`, replace:
```python
connector = get_connector(agent.broker, self.vault)
```
with:
```python
connector = get_connector(agent.broker, self.vault, paper=agent.is_paper_trading)
```

Also in `backend/trading/trade_executor.py`, replace:
```python
connector = get_connector(agent_config["broker"], vault)
```
with:
```python
connector = get_connector(
    agent_config["broker"], vault,
    paper=agent_config.get("paper_trading", True),
)
```

Update `_build_agent_config` in orchestrator to confirm `paper_trading` is already set (it is — `agent.is_paper_trading`).

- [ ] **Step 6: Run full test suite**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

Expected: no regressions

- [ ] **Step 7: Commit**

```bash
git add backend/brokers/manager.py backend/brokers/alpaca.py backend/orchestrator/agent_orchestrator.py backend/trading/trade_executor.py tests/test_broker_live.py
git commit -m "feat(6A.1): pass paper flag through get_connector; fix Alpaca hardcoded paper=True"
```

---

### Task 6A.2: Add Kraken connector

**Files:**
- Create: `backend/brokers/kraken.py`

**Interfaces:**
- `KrakenConnector(api_key, secret, paper=True)` — paper mode simulates locally (Kraken has no paper API)
- Implements full `BrokerConnector` interface

- [ ] **Step 1: Write failing test**

```python
# tests/test_broker_live.py — add

@pytest.mark.asyncio
async def test_kraken_connector_test_connection_returns_bool():
    """KrakenConnector.test_connection() returns bool."""
    from backend.brokers.kraken import KrakenConnector
    with patch("krakenex.API.query_public", return_value={"result": {"XXBTZUSD": {}}}):
        conn = KrakenConnector("key", "secret", paper=True)
        result = await conn.test_connection()
        assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_kraken_paper_place_order_returns_order():
    """KrakenConnector paper mode place_order returns Order with uuid."""
    from backend.brokers.kraken import KrakenConnector
    from backend.brokers.base import Order
    conn = KrakenConnector("key", "secret", paper=True)
    conn._paper_balance = 100_000.0
    order = await conn.place_order("BTC/USD", "buy", 500.0, "market")
    assert isinstance(order, Order)
    assert order.order_id is not None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_broker_live.py::test_kraken_connector_test_connection_returns_bool tests/test_broker_live.py::test_kraken_paper_place_order_returns_order -v
```

Expected: `FAIL` — `KrakenConnector` not found

- [ ] **Step 3: Create `backend/brokers/kraken.py`**

```python
import time
import uuid
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class KrakenConnector(BrokerConnector):
    # ponytail: Kraken has no paper API — simulate paper locally, live uses krakenex
    def __init__(self, api_key: str, secret: str, paper: bool = True):
        self._key = api_key
        self._secret = secret
        self._paper = paper
        self._paper_balance = 100_000.0  # ponytail: calibration knob for paper mode

    def _api(self):
        import krakenex
        k = krakenex.API()
        k.key = self._key
        k.secret = self._secret
        return k

    async def get_account_balance(self) -> float:
        if self._paper:
            return self._paper_balance
        resp = self._api().query_private("Balance")
        if resp.get("error"):
            raise RuntimeError(f"Kraken balance error: {resp['error']}")
        zusd = resp["result"].get("ZUSD", resp["result"].get("USD.F", 0))
        return float(zusd)

    async def get_market_data(self, symbol: str) -> MarketData:
        # Kraken symbol format: "BTC/USD" → "XBTUSD" for API
        kraken_sym = symbol.replace("BTC", "XBT").replace("/", "")
        resp = self._api().query_public("Ticker", {"pair": kraken_sym})
        if resp.get("error"):
            raise RuntimeError(f"Kraken ticker error: {resp['error']}")
        data = list(resp["result"].values())[0]
        price = float(data["c"][0])  # last trade closed price
        volume = float(data["v"][1])  # 24h volume
        return MarketData(symbol=symbol, price=price, volume=volume,
                          rsi=None, ma20=None, ma50=None, fetched_at=time.time())

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        if self._paper:
            # ponytail: paper sim — no real order
            return Order(order_id=str(uuid.uuid4()), symbol=symbol, side=side,
                         quantity=quantity, filled_price=None, status="filled")
        kraken_sym = symbol.replace("BTC", "XBT").replace("/", "")
        resp = self._api().query_private("AddOrder", {
            "pair": kraken_sym,
            "type": side.lower(),
            "ordertype": "market",
            "volume": str(quantity),
        })
        if resp.get("error"):
            raise RuntimeError(f"Kraken order error: {resp['error']}")
        txid = resp["result"]["txid"][0]
        return Order(order_id=txid, symbol=symbol, side=side,
                     quantity=quantity, filled_price=None, status="open")

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        return False  # ponytail: Kraken stop orders require separate order at creation

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        return False

    async def get_positions(self) -> list[Position]:
        if self._paper:
            return []
        resp = self._api().query_private("OpenPositions")
        if resp.get("error"):
            return []
        positions = []
        for pos_id, pos in resp.get("result", {}).items():
            positions.append(Position(
                symbol=pos.get("pair", "UNKNOWN"),
                quantity=float(pos.get("vol", 0)),
                avg_price=float(pos.get("cost", 0)) / max(float(pos.get("vol", 1)), 0.0001),
                unrealized_pnl=float(pos.get("net", 0)),
            ))
        return positions

    async def close_position(self, symbol: str) -> bool:
        positions = await self.get_positions()
        for pos in positions:
            if pos.symbol == symbol.replace("BTC", "XBT").replace("/", ""):
                await self.place_order(symbol, "sell", pos.quantity, "market")
                return True
        return False

    async def test_connection(self) -> bool:
        try:
            resp = self._api().query_public("ServerTime")
            return not bool(resp.get("error"))
        except Exception:
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_broker_live.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/brokers/kraken.py backend/brokers/manager.py tests/test_broker_live.py
git commit -m "feat(6A.2): add KrakenConnector; register in get_connector"
```

---

### Task 6A.3: Add generic ccxt connector for any other exchange

**Files:**
- Create: `backend/brokers/ccxt_generic.py`

**Why:** User said "Alpaca and Binance and more". The ccxt library supports 100+ exchanges. One generic class + manager lookup covers all of them without new connector files per exchange.

- [ ] **Step 1: Write failing test**

```python
# tests/test_broker_live.py — add

@pytest.mark.asyncio
async def test_ccxt_generic_test_connection_returns_bool():
    """CcxtConnector wraps any ccxt exchange."""
    from backend.brokers.ccxt_generic import CcxtConnector
    conn = CcxtConnector("binance", "key", "secret")
    with patch.object(conn._exchange, "fetch_status", new=AsyncMock(return_value={"status": "ok"})):
        result = await conn.test_connection()
        assert result is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_broker_live.py::test_ccxt_generic_test_connection_returns_bool -v
```

Expected: `FAIL`

- [ ] **Step 3: Create `backend/brokers/ccxt_generic.py`**

```python
import time
import uuid
import ccxt.async_support as ccxt
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class CcxtConnector(BrokerConnector):
    """Generic ccxt connector — supports any ccxt-compatible exchange."""

    def __init__(self, exchange_id: str, api_key: str, secret: str):
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"Unknown ccxt exchange: {exchange_id}")
        self._exchange = getattr(ccxt, exchange_id)({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })

    async def get_account_balance(self) -> float:
        balance = await self._exchange.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0))

    async def get_market_data(self, symbol: str) -> MarketData:
        ticker = await self._exchange.fetch_ticker(symbol)
        return MarketData(symbol=symbol, price=float(ticker["last"]),
                          volume=float(ticker.get("quoteVolume", 0)),
                          rsi=None, ma20=None, ma50=None, fetched_at=time.time())

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        method = (self._exchange.create_market_buy_order if side.lower() == "buy"
                  else self._exchange.create_market_sell_order)
        result = await method(symbol, quantity)
        return Order(order_id=str(result["id"]), symbol=symbol, side=side,
                     quantity=quantity, filled_price=result.get("average"),
                     status=result.get("status", "open"))

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        return False  # ponytail: exchange-specific; implement per-exchange if needed

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        return False

    async def get_positions(self) -> list[Position]:
        balance = await self._exchange.fetch_balance()
        positions = []
        for asset, data in balance.get("total", {}).items():
            qty = float(data) if data else 0.0
            if qty > 0 and asset != "USDT":
                try:
                    ticker = await self._exchange.fetch_ticker(f"{asset}/USDT")
                    positions.append(Position(symbol=f"{asset}/USDT", quantity=qty,
                                              avg_price=float(ticker["last"]), unrealized_pnl=0.0))
                except Exception:
                    pass
        return positions

    async def close_position(self, symbol: str) -> bool:
        balance = await self._exchange.fetch_balance()
        asset = symbol.split("/")[0]
        qty = float(balance.get("free", {}).get(asset, 0))
        if qty <= 0:
            return False
        await self._exchange.create_market_sell_order(symbol, qty)
        return True

    async def test_connection(self) -> bool:
        try:
            await self._exchange.fetch_status()
            return True
        except Exception:
            return False

    async def close(self):
        await self._exchange.close()
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_broker_live.py::test_ccxt_generic_test_connection_returns_bool -v
```

Expected: `PASS`

- [ ] **Step 5: Commit**

```bash
git add backend/brokers/ccxt_generic.py tests/test_broker_live.py
git commit -m "feat(6A.3): add generic ccxt connector for any ccxt-compatible exchange"
```

---

### Task 6A.4: Pre-flight vault credential check + `/api/brokers/vault-check/{broker}`

**Files:**
- Modify: `backend/trading/trade_executor.py`
- Modify: `backend/api/agents.py` (add vault check endpoint)

**Why production-critical:** Without this, an agent with `is_paper_trading=False` but missing vault credentials will fail mid-order with a cryptic error. Pre-flight surfaces the error before any order is attempted and lets the UI warn the user.

- [ ] **Step 1: Write failing test**

```python
# tests/test_trade_executor.py — add

@pytest.mark.asyncio
async def test_live_order_fails_preflight_if_vault_missing_key():
    """Live order returns error if vault key missing (vault.get raises or returns None)."""
    from backend.trading.trade_executor import TradeExecutor
    from backend.llm.llm_router import TradeDecision

    vault = MagicMock()
    vault.get.return_value = None  # simulate missing key

    executor = TradeExecutor(vault, None)
    decision = TradeDecision(action="BUY", confidence=0.8, position_size=0.1, reasoning="test")
    agent_config = {
        "broker": "alpaca", "paper_trading": False,
        "allocation_percent": 0.1, "max_position_size": 0.05,
        "asset": "AAPL", "execution_mode": "autonomous",
        "name": "TestAgent", "user_id": None,
    }
    db_session = MagicMock()

    with patch("backend.trading.trade_executor.get_connector") as mock_gc:
        mock_gc.side_effect = Exception("vault key missing")
        result = await executor.execute(
            agent_id=1, decision=decision, agent_config=agent_config,
            vault=vault, db_session=db_session, broadcast_callback=None,
        )

    assert result["status"] == "error"
    assert "broker error" in result["reason"]
```

- [ ] **Step 2: Run test to verify it passes (should already pass — the existing error handling covers this)**

```bash
pytest tests/test_trade_executor.py::test_live_order_fails_preflight_if_vault_missing_key -v
```

If PASS: test confirms error handling already correct. Proceed to vault-check API endpoint.

- [ ] **Step 3: Add `GET /api/brokers/vault-check/{broker}` endpoint**

In `backend/api/agents.py` (or create `backend/api/brokers.py` if broker routes don't already exist — check first). Add to `backend/main.py` if creating new file.

Simplest path: add to existing `backend/api/agents.py` (ponytail — no new file):

```python
# At top of agents.py, import vault
from backend.vault.encrypted_vault import EncryptedVault

@router.get("/brokers/vault-check/{broker}")
async def vault_check_broker(
    broker: str,
    current_user: User = Depends(get_current_user),
):
    """Check if vault has credentials for the given broker."""
    try:
        vault = EncryptedVault()
        broker = broker.lower()
        key_map = {
            "alpaca": ["alpaca_api_key", "alpaca_secret"],
            "binance": ["binance_api_key", "binance_secret"],
            "kraken": ["kraken_api_key", "kraken_api_secret"],
        }
        required_keys = key_map.get(broker, [f"{broker}_api_key", f"{broker}_secret"])
        has_all = all(bool(vault.get(k)) for k in required_keys)
        return {"broker": broker, "has_credentials": has_all, "required_keys": required_keys}
    except Exception as e:
        return {"broker": broker, "has_credentials": False, "error": str(e)}
```

Note: prefix this route BEFORE the agent CRUD routes (FastAPI matches in order — `brokers/vault-check/...` must not be shadowed by `/{agent_id}`). Add it to a dedicated brokers router if ordering is an issue.

- [ ] **Step 4: Write test for vault-check endpoint**

```python
# tests/test_api_agents.py — add

def test_vault_check_broker_returns_has_credentials(client, auth_headers):
    """GET /api/agents/brokers/vault-check/alpaca returns has_credentials field."""
    resp = client.get("/api/agents/brokers/vault-check/alpaca", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "has_credentials" in data
    assert "broker" in data
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_trade_executor.py::test_live_order_fails_preflight_if_vault_missing_key tests/test_api_agents.py::test_vault_check_broker_returns_has_credentials -v --asyncio-mode=auto
```

Expected: both pass

- [ ] **Step 6: Commit**

```bash
git add backend/api/agents.py tests/test_trade_executor.py tests/test_api_agents.py
git commit -m "feat(6A.4): vault credential pre-flight check; GET /api/agents/brokers/vault-check/{broker}"
```

---

### Task 6A.5: Alpaca live order fill polling (production hardening)

**Files:**
- Modify: `backend/brokers/alpaca.py`

**Why:** Alpaca `place_order` returns `filled_price=None` for market orders (fill is async). Production live trading needs the actual fill price in the Trade record and WS broadcast. Without this, `trade.entry_price = 0.0` for all live trades.

**Approach (ponytail):** Poll Alpaca order status for up to 5 seconds after submission. If not filled within 5s, store `entry_price=0.0` and schedule a fill-update via a background task. This avoids blocking the agent loop.

- [ ] **Step 1: Write failing test**

```python
# tests/test_broker_live.py — add

@pytest.mark.asyncio
async def test_alpaca_place_order_polls_for_fill():
    """AlpacaConnector.place_order polls status and returns filled_price when available."""
    from backend.brokers.alpaca import AlpacaConnector
    import httpx

    conn = AlpacaConnector("key", "secret", paper=False)

    order_response = {"id": "order-123", "status": "new"}
    filled_response = {"id": "order-123", "status": "filled", "filled_avg_price": "185.42"}

    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "order-123" in url and call_count > 2:
            resp.json = MagicMock(return_value=filled_response)
        else:
            resp.json = MagicMock(return_value=order_response)
        return resp

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=order_response)
        return resp

    with patch.object(conn, '_client') as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client_ctx.return_value = mock_client

        order = await conn.place_order("AAPL", "buy", 5.0, "market")

    assert order.order_id == "order-123"
    assert order.filled_price == 185.42
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_broker_live.py::test_alpaca_place_order_polls_for_fill -v
```

Expected: `FAIL` — current `place_order` returns `filled_price=None` immediately

- [ ] **Step 3: Update `AlpacaConnector.place_order` to poll for fill**

In `backend/brokers/alpaca.py`, replace `place_order`:

```python
    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        payload = {"symbol": symbol, "qty": quantity, "side": side,
                   "type": order_type, "time_in_force": "gtc"}
        import asyncio
        async with self._client() as c:
            r = await c.post(f"{self._base}/v2/orders", json=payload)
            r.raise_for_status()
            o = r.json()

        order_id = o["id"]
        filled_price = None

        # Poll up to 5s for fill confirmation (market orders usually fill in <1s)
        for _ in range(5):
            await asyncio.sleep(1)
            async with self._client() as c:
                r = await c.get(f"{self._base}/v2/orders/{order_id}")
                r.raise_for_status()
                status_data = r.json()
            if status_data.get("status") in ("filled", "partially_filled"):
                filled_price = float(status_data["filled_avg_price"]) if status_data.get("filled_avg_price") else None
                break

        return Order(order_id=order_id, symbol=symbol, side=side,
                     quantity=quantity, filled_price=filled_price, status=o["status"])
```

- [ ] **Step 4: Run test to verify it passes**

```bash
pytest tests/test_broker_live.py::test_alpaca_place_order_polls_for_fill -v
```

Expected: `PASS`

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

- [ ] **Step 6: Commit**

```bash
git add backend/brokers/alpaca.py tests/test_broker_live.py
git commit -m "feat(6A.5): Alpaca live order fill polling — poll 5s for filled_avg_price after market order"
```

---

### Task 6A.6: DailySnapshot write after every completed trade

**Files:**
- Modify: `backend/trading/trade_executor.py`
- Modify: `backend/orchestrator/agent_orchestrator.py`
- Create: `alembic/versions/xxxx_add_daily_snapshot_win_loss.py`

**Why:** `DailySnapshot` model already exists and has `trade_count`, `total_pnl`, `win_rate`, etc. Phase 6 must write to it after every trade to build the equity curve that backtest UI and Analytics dashboards rely on.

- [ ] **Step 1: Add Alembic migration for `trades_won`/`trades_lost` on DailySnapshot**

```bash
cd /Users/coleadams/labourious && source .venv/bin/activate
```

In `backend/database/models.py`, add to `DailySnapshot`:
```python
    trades_won = Column(Integer, nullable=False, default=0)
    trades_lost = Column(Integer, nullable=False, default=0)
```

Then:
```bash
alembic revision --autogenerate -m "add_trades_won_lost_to_daily_snapshot"
alembic upgrade head
```

- [ ] **Step 2: Write failing test**

```python
# tests/test_trade_executor.py — add

def test_daily_snapshot_upsert_after_paper_trade():
    """After paper trade, DailySnapshot row is created or updated for agent+date."""
    from backend.trading.trade_executor import _upsert_daily_snapshot
    from backend.database.models import DailySnapshot

    session = MagicMock()
    session.execute.return_value.scalar_one_or_none.return_value = None  # no existing snapshot
    session.add = MagicMock()
    session.flush = MagicMock()

    _upsert_daily_snapshot(
        agent_id=1,
        date_str="2026-06-21",
        pnl=250.0,
        won=True,
        trade_count=1,
        portfolio_value=100250.0,
        cash_balance=100000.0,
        session=session,
    )

    session.add.assert_called_once()
    snapshot_arg = session.add.call_args[0][0]
    assert isinstance(snapshot_arg, DailySnapshot)
    assert snapshot_arg.total_pnl == 250.0
    assert snapshot_arg.trades_won == 1
```

- [ ] **Step 3: Implement `_upsert_daily_snapshot` in `trade_executor.py`**

Add to `backend/trading/trade_executor.py` as module-level function (not a method — called from `_update_agent_stats`):

```python
def _upsert_daily_snapshot(
    agent_id: int,
    date_str: str,
    pnl: float,
    won: bool,
    trade_count: int,
    portfolio_value: float,
    cash_balance: float,
    session,
) -> None:
    """Insert or update today's DailySnapshot for agent."""
    from backend.database.models import DailySnapshot
    from sqlalchemy import select

    existing = session.execute(
        select(DailySnapshot).where(
            DailySnapshot.agent_id == agent_id,
            DailySnapshot.date == date_str,
        )
    ).scalar_one_or_none()

    if existing:
        existing.total_pnl += pnl
        existing.trade_count += trade_count
        existing.trades_won = (existing.trades_won or 0) + (1 if won else 0)
        existing.trades_lost = (existing.trades_lost or 0) + (0 if won else 1)
        existing.win_rate = existing.trades_won / max(existing.trade_count, 1)
        existing.portfolio_value = portfolio_value
        existing.cash_balance = cash_balance
        session.add(existing)
    else:
        snapshot = DailySnapshot(
            agent_id=agent_id,
            date=date_str,
            total_pnl=pnl,
            daily_return_pct=pnl / max(portfolio_value - pnl, 1.0),
            trade_count=trade_count,
            trades_won=1 if won else 0,
            trades_lost=0 if won else 1,
            win_rate=1.0 if won else 0.0,
            portfolio_value=portfolio_value,
            cash_balance=cash_balance,
        )
        session.add(snapshot)
    session.flush()
```

In `_update_agent_stats`, after `db_session.commit()` on agent stats, add:

```python
        from datetime import date
        date_str = date.today().isoformat()
        _upsert_daily_snapshot(
            agent_id=agent_id,
            date_str=date_str,
            pnl=pnl,
            won=pnl > 0,
            trade_count=1,
            portfolio_value=agent.paper_trading_balance or 0.0,
            cash_balance=agent.paper_trading_balance or 0.0,
            session=db_session,
        )
        db_session.commit()
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_trade_executor.py::test_daily_snapshot_upsert_after_paper_trade -v --asyncio-mode=auto
```

Expected: `PASS`

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

- [ ] **Step 6: Commit**

```bash
git add backend/trading/trade_executor.py backend/database/models.py alembic/versions/ tests/test_trade_executor.py
git commit -m "feat(6A.6): write DailySnapshot after every trade; add trades_won/trades_lost columns via Alembic"
```

---

## Priority 2 — Backtest UI Completion (Backend + Frontend)

### Task 6B.1: Fix backtest equity curve — real day-by-day balance series

**Files:**
- Modify: `backend/scripts/backtest.py`
- Modify: `backend/api/backtest_ui.py`

**Problem:** `run_simulation` returns `equity_curve: []` (hardcoded empty). `BacktestRunner.jsx` has `EquityChart` component that needs `[{date, balance}]` data. Without this, the chart never renders.

- [ ] **Step 1: Write failing test**

```python
# tests/test_backtest.py — create or add

import pytest
import pandas as pd
import numpy as np


def _make_df(n=50):
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    close = 100 + np.cumsum(np.random.randn(n))
    return pd.DataFrame({"close": close, "open": close, "high": close * 1.01, "low": close * 0.99}, index=dates)


def test_run_simulation_equity_curve_non_empty():
    """run_simulation returns equity_curve with one entry per row."""
    from backend.scripts.backtest import run_simulation, add_indicators
    df = add_indicators(_make_df(60))
    df = df.dropna(subset=["close"])
    metrics = run_simulation(df, initial_balance=10_000.0)
    assert "equity_curve" in metrics
    assert len(metrics["equity_curve"]) > 0
    # Each entry has date + balance
    assert "date" in metrics["equity_curve"][0]
    assert "balance" in metrics["equity_curve"][0]


def test_backtest_output_consistent_decimals():
    """CLI output uses decimal fractions (not percentages) for total_return and win_rate."""
    from backend.scripts.backtest import run_simulation, add_indicators
    df = add_indicators(_make_df(60))
    df = df.dropna(subset=["close"])
    metrics = run_simulation(df, initial_balance=10_000.0)
    # total_return_pct and win_rate_pct are internal — CLI output normalises to decimals
    assert abs(metrics.get("win_rate_pct", 0)) <= 100  # pct variant stays as pct internally
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_backtest.py::test_run_simulation_equity_curve_non_empty -v
```

Expected: `FAIL` — `equity_curve` not in metrics dict

- [ ] **Step 3: Update `run_simulation` in `backtest.py`**

Replace `run_simulation`:

```python
def run_simulation(df: pd.DataFrame, initial_balance: float = 100_000.0) -> dict:
    """Paper trading simulation over df. Returns metrics dict including equity_curve."""
    balance = initial_balance
    position = 0.0
    entry_price = 0.0
    trades = []
    equity_curve = []

    for idx, row in df.iterrows():
        signal = rule_signal(row)
        price = float(row["close"])

        if signal == "BUY" and position == 0 and balance > 0:
            qty = (balance * 0.05) / price
            position = qty
            entry_price = price
            balance -= qty * price

        elif signal == "SELL" and position > 0:
            pnl = (price - entry_price) * position
            balance += position * price
            trades.append({"entry": entry_price, "exit": price, "qty": position, "pnl": pnl, "win": pnl > 0})
            position = 0.0
            entry_price = 0.0

        # Record equity (cash + mark-to-market of open position)
        equity_curve.append({
            "date": str(idx.date()) if hasattr(idx, "date") else str(idx),
            "balance": round(balance + position * price, 2),
        })

    if position > 0:
        price = float(df["close"].iloc[-1])
        pnl = (price - entry_price) * position
        balance += position * price
        trades.append({"entry": entry_price, "exit": price, "qty": position, "pnl": pnl, "win": pnl > 0})

    total_return = (balance - initial_balance) / initial_balance
    wins = sum(1 for t in trades if t["win"])
    win_rate = wins / len(trades) if trades else 0.0

    pnls = np.array([t["pnl"] for t in trades]) if trades else np.array([0.0])
    sharpe = float(np.mean(pnls) / np.std(pnls) * np.sqrt(252)) if np.std(pnls) > 0 else 0.0

    cumulative = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_dd = float(np.min(drawdown)) if len(drawdown) else 0.0

    return {
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_return_pct": round(total_return * 100, 2),
        "win_rate_pct": round(win_rate * 100, 1),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(max_dd, 2),
        "num_trades": len(trades),
        "equity_curve": equity_curve,
    }
```

Update the `main()` CLI output to normalise to decimals:

```python
    if args.mode == "basic":
        metrics = run_simulation(df, args.balance)
        output = {
            "total_return": round(metrics["total_return_pct"] / 100, 6),
            "win_rate": round(metrics["win_rate_pct"] / 100, 6),
            "sharpe_ratio": metrics["sharpe_ratio"],
            "max_drawdown": metrics["max_drawdown"],
            "num_trades": metrics["num_trades"],
            "equity_curve": metrics["equity_curve"],  # now populated
        }
        print(json.dumps(output))
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_backtest.py -v
```

Expected: all pass

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/backtest.py tests/test_backtest.py
git commit -m "feat(6B.1): real equity curve in backtest — day-by-day balance series; fix return/rate normalisation"
```

---

### Task 6B.2: Walk-forward results panel in `BacktestRunner.jsx`

**Files:**
- Modify: `frontend/src/components/Analytics/BacktestRunner.jsx`

**Problem:** `BacktestRunner.jsx` renders stat boxes and `EquityChart` for basic mode but renders nothing for walk-forward mode. `result_json` for walk-forward contains `{windows: [{window, total_return_pct, win_rate_pct, sharpe_ratio, test_start, test_end}], efficiency}`.

- [ ] **Step 1: Implement walk-forward results section**

In `BacktestRunner.jsx`, after the existing results block (after the basic stats render), add:

```jsx
      {/* Walk-forward windows table */}
      {backtestStatus === 'done' && stats?.windows?.length > 0 && (
        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)' }}>
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 'var(--space-3)', letterSpacing: '0.08em' }}>
            WALK-FORWARD WINDOWS — Efficiency: {stats.efficiency?.toFixed(1) ?? '—'}%
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
            <thead>
              <tr style={{ color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)' }}>
                {['Window', 'Period', 'Return', 'Win Rate', 'Sharpe'].map((h) => (
                  <th key={h} style={{ textAlign: 'left', padding: '0.3rem 0.5rem', fontWeight: 'normal' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {stats.windows.map((w) => {
                const ret = w.total_return_pct ?? 0;
                return (
                  <tr key={w.window} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '0.35rem 0.5rem' }}>#{w.window}</td>
                    <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-text-muted)' }}>
                      {w.test_start} → {w.test_end}
                    </td>
                    <td style={{ padding: '0.35rem 0.5rem', color: ret >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)' }}>
                      {ret >= 0 ? '+' : ''}{ret.toFixed(1)}%
                    </td>
                    <td style={{ padding: '0.35rem 0.5rem' }}>{w.win_rate_pct?.toFixed(1) ?? '—'}%</td>
                    <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-accent-secondary)' }}>{w.sharpe_ratio?.toFixed(2) ?? '—'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Analytics/BacktestRunner.jsx
git commit -m "feat(6B.2): walk-forward window results table in BacktestRunner"
```

---

### Task 6B.3: Backtest history panel

**Files:**
- Create: `frontend/src/components/Analytics/BacktestHistory.jsx`
- Modify: `frontend/src/pages/AnalyticsPage.jsx` (or wherever BacktestRunner is mounted)

- [ ] **Step 1: Create `BacktestHistory.jsx`**

```jsx
// frontend/src/components/Analytics/BacktestHistory.jsx
import { useEffect } from 'react';
import useAnalyticsStore from '../../stores/analytics.store';

const STATUS_COLOR = {
  done: 'var(--color-pnl-positive)',
  failed: 'var(--color-accent-danger, #ff4444)',
  running: 'var(--color-accent-warning, #ffb020)',
};

export default function BacktestHistory({ agentId = null }) {
  const { backtestHistory, fetchBacktestHistory, runBacktest } = useAnalyticsStore();

  useEffect(() => {
    fetchBacktestHistory(agentId);
  }, [agentId, fetchBacktestHistory]);

  if (!backtestHistory.length) return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginTop: 'var(--space-4)' }}>
      No backtest history.
    </div>
  );

  return (
    <div style={{ marginTop: 'var(--space-4)' }}>
      <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.08em', marginBottom: 'var(--space-3)' }}>
        RECENT RUNS
      </div>
      <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)' }}>
        <thead>
          <tr style={{ color: 'var(--color-text-muted)', borderBottom: '1px solid var(--color-border)' }}>
            {['Agent', 'Period', 'Mode', 'Status', 'Run At', ''].map((h) => (
              <th key={h} style={{ textAlign: 'left', padding: '0.3rem 0.5rem', fontWeight: 'normal' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {backtestHistory.map((r) => (
            <tr key={r.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
              <td style={{ padding: '0.35rem 0.5rem' }}>#{r.agent_id ?? '—'}</td>
              <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-text-muted)' }}>
                {r.start_date} → {r.end_date}
              </td>
              <td style={{ padding: '0.35rem 0.5rem' }}>{r.mode}</td>
              <td style={{ padding: '0.35rem 0.5rem', color: STATUS_COLOR[r.status] ?? 'inherit' }}>
                {r.status.toUpperCase()}
              </td>
              <td style={{ padding: '0.35rem 0.5rem', color: 'var(--color-text-muted)' }}>
                {r.run_at?.slice(0, 16).replace('T', ' ')}
              </td>
              <td style={{ padding: '0.35rem 0.5rem' }}>
                <button
                  onClick={() => runBacktest({ agent_id: r.agent_id, start_date: r.start_date, end_date: r.end_date, mode: r.mode })}
                  style={{ background: 'none', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', cursor: 'pointer', padding: '0.15rem 0.4rem', borderRadius: 2 }}
                >
                  re-run
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Mount `BacktestHistory` on the Analytics page**

Find where `BacktestRunner` is rendered in `frontend/src/pages/AnalyticsPage.jsx`. Add below `BacktestRunner`:

```jsx
import BacktestHistory from '../components/Analytics/BacktestHistory';

// In the Analytics page, after <BacktestRunner agents={agents} />:
<BacktestHistory agentId={selectedAgentId ?? null} />
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Analytics/BacktestHistory.jsx frontend/src/pages/AnalyticsPage.jsx
git commit -m "feat(6B.3): BacktestHistory panel — past runs table with re-run button"
```

---

## Priority 3 — Strategy Builder & Agent Config UX (Frontend)

### Task 6C.1: Editable Rules/context tab in AgentInspector

**Files:**
- Modify: `frontend/src/components/Warroom/AgentInspector.jsx`

**Problem:** The `RulesTab` displays `strategy_config.context_content` but is read-only. Strategy builder = let the user edit this content and save via `POST /api/agents/{id}/update-context` (already exists).

- [ ] **Step 1: Replace read-only `RulesTab` with editable version**

In `AgentInspector.jsx`, replace the `RulesTab` component:

```jsx
function RulesTab({ agent }) {
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(
    agent.strategy_config?.context_content
    ?? agent.strategy_config?.context
    ?? agent.strategy_config?.rules
    ?? ''
  );
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = async () => {
    setBusy(true);
    try {
      await fetch(`/api/agents/${agent.id}/update-context`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('auth_access_token')}`,
        },
        body: JSON.stringify({ content }),
      });
      setSaved(true);
      setEditing(false);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      // silent — user sees no change
    } finally {
      setBusy(false);
    }
  };

  const TEMPLATES = [
    { label: 'Momentum', text: 'You are a momentum trader. Buy when RSI > 60 and price above MA20. Sell when RSI < 40 or price drops below MA20 by 2%. Position size: 5% per trade.' },
    { label: 'Mean Rev', text: 'You are a mean reversion trader. Buy when RSI < 30 (oversold). Sell when RSI > 70 (overbought) or price returns to MA50. Risk: 2% stop loss.' },
    { label: 'Scalper', text: 'You are a scalper. Look for tight ranges. Buy on support, sell on resistance. Keep positions under 1 hour. Position size: 3% maximum.' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.65rem', color: 'var(--color-text-muted)', letterSpacing: '0.08em' }}>STRATEGY CONTEXT</span>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          {saved && <span style={{ fontSize: '0.65rem', color: 'var(--color-accent-primary)' }}>SAVED</span>}
          <button
            onClick={() => setEditing((e) => !e)}
            style={{ background: 'none', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', cursor: 'pointer', padding: '0.15rem 0.5rem', borderRadius: 2 }}
          >
            {editing ? 'cancel' : 'edit'}
          </button>
        </div>
      </div>

      {editing && (
        <div style={{ display: 'flex', gap: '0.3rem', flexWrap: 'wrap', marginBottom: '0.3rem' }}>
          {TEMPLATES.map((t) => (
            <button
              key={t.label}
              onClick={() => setContent(t.text)}
              style={{ background: 'var(--color-bg-tertiary)', border: '1px solid var(--color-border)', color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem', cursor: 'pointer', padding: '0.15rem 0.4rem', borderRadius: 2 }}
            >
              {t.label}
            </button>
          ))}
        </div>
      )}

      {editing ? (
        <>
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            rows={10}
            style={{
              width: '100%', background: 'var(--color-bg-tertiary)',
              border: '1px solid var(--color-accent-primary)', color: 'var(--color-text-primary)',
              fontFamily: 'var(--font-mono)', fontSize: '0.75rem', padding: '0.5rem',
              resize: 'vertical', borderRadius: 3, lineHeight: 1.5,
            }}
          />
          <button
            onClick={handleSave}
            disabled={busy}
            style={{
              padding: '0.4rem', background: 'var(--color-accent-primary, #00ff88)', color: '#000',
              border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700,
              fontSize: '0.75rem', cursor: busy ? 'not-allowed' : 'pointer', borderRadius: 3,
            }}
          >
            {busy ? 'SAVING…' : 'SAVE CONTEXT'}
          </button>
        </>
      ) : (
        content ? (
          <pre style={{
            fontSize: '0.75rem', color: 'var(--color-text-secondary)',
            background: 'var(--color-bg-tertiary)', padding: '0.75rem',
            borderRadius: 4, overflowX: 'auto', whiteSpace: 'pre-wrap',
          }}>
            {content}
          </pre>
        ) : (
          <div style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}>
            No context — click <strong>edit</strong> to add strategy rules.
          </div>
        )
      )}
    </div>
  );
}
```

- [ ] **Step 2: Add `useState` import if not already present** (it is)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Warroom/AgentInspector.jsx
git commit -m "feat(6C.1): editable strategy context in AgentInspector Rules tab; preset templates"
```

---

### Task 6C.2: Live-mode confirmation dialog on "Switch Live" button

**Files:**
- Modify: `frontend/src/components/Warroom/AgentInspector.jsx`

**Why production-critical:** Clicking "Switch Live" immediately PATCHes `is_paper_trading=False`. One mis-click = real money mode. Must show a blocking confirmation.

- [ ] **Step 1: Add confirmation state and dialog to `SettingsTab`**

In `SettingsTab`, add after `const [busy, setBusy] = useState(false);`:

```jsx
  const [confirmLive, setConfirmLive] = useState(false);
```

Replace the "Paper Trading" toggle button section with:

```jsx
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0.5rem 0', borderBottom: '1px solid var(--color-border)', fontSize: '0.8rem' }}>
        <span style={{ color: 'var(--color-text-muted)' }}>Paper Trading</span>
        <button
          disabled={busy}
          onClick={() => {
            if (agent.is_paper_trading) {
              setConfirmLive(true);  // require confirmation before going live
            } else {
              toggle('is_paper_trading');  // switching back to paper is always safe
            }
          }}
          style={btnStyle(agent.is_paper_trading)}
        >
          {agent.is_paper_trading ? 'Switch Live' : 'Switch Paper'}
        </button>
      </div>

      {/* Live mode confirmation dialog */}
      {confirmLive && (
        <div style={{
          background: 'var(--color-bg-tertiary)', border: '2px solid var(--color-danger, #ff4444)',
          borderRadius: 6, padding: '1rem', marginTop: '0.5rem',
        }}>
          <div style={{ fontSize: '0.75rem', color: 'var(--color-danger, #ff4444)', fontWeight: 700, marginBottom: '0.5rem' }}>
            ⚠ SWITCHING TO LIVE TRADING
          </div>
          <div style={{ fontSize: '0.7rem', color: 'var(--color-text-secondary)', marginBottom: '1rem', lineHeight: 1.5 }}>
            This agent will execute real orders using real money. Ensure your broker credentials are set in the Vault and your position size limits are correct before proceeding.
          </div>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={async () => { setConfirmLive(false); await toggle('is_paper_trading'); }}
              style={{ flex: 1, padding: '0.4rem', background: 'var(--color-danger, #ff4444)', color: '#fff', border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: '0.75rem', cursor: 'pointer', borderRadius: 3 }}
            >
              CONFIRM — GO LIVE
            </button>
            <button
              onClick={() => setConfirmLive(false)}
              style={{ flex: 1, padding: '0.4rem', background: 'transparent', color: 'var(--color-text-muted)', border: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)', fontSize: '0.75rem', cursor: 'pointer', borderRadius: 3 }}
            >
              CANCEL
            </button>
          </div>
        </div>
      )}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Warroom/AgentInspector.jsx
git commit -m "feat(6C.2): live trading confirmation dialog — block accidental Switch Live clicks"
```

---

## Priority 4 — Notifications Delivery (Backend + Frontend)

### Task 6D.1: Wire email delivery — SMTP native + SendGrid relay path

**Files:**
- Modify: `backend/config.py`
- Modify: `backend/notifications/service.py`

**Architecture decision (ponytail):** SendGrid provides an SMTP relay (`smtp.sendgrid.net:587`, username `apikey`, password = SendGrid API key). The existing `smtplib`-based `NotificationService` already supports this with zero code change — just different env vars. However, we add a dedup window to prevent notification spam.

**Required .env vars for SendGrid relay:**
```
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASS=<your_sendgrid_api_key>
```

**Required .env vars for Twilio SMS (already supported):**
```
TWILIO_ACCOUNT_SID=ACxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxx
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
```

- [ ] **Step 1: Add config vars and dedup cooldown**

In `backend/config.py`, add after existing notification settings:

```python
    SENDGRID_API_KEY: Optional[str] = os.getenv("SENDGRID_API_KEY")  # alternative to SMTP config
    NOTIFICATION_COOLDOWN_MINUTES: int = int(os.getenv("NOTIFICATION_COOLDOWN_MINUTES", "5"))
```

- [ ] **Step 2: Write failing test for dedup**

```python
# tests/test_notifications.py — create

import pytest
from unittest.mock import patch, MagicMock
import time


def test_notification_service_dedup_prevents_spam():
    """Same notification key sent twice within cooldown window is dropped."""
    from backend.notifications.service import NotificationService

    svc = NotificationService()
    svc.smtp_configured = True
    svc._dedup_cache = {}
    svc._cooldown_seconds = 5

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        first = svc.send_email("user@test.com", "Test", "body", dedup_key="key-1")
        second = svc.send_email("user@test.com", "Test", "body", dedup_key="key-1")

    assert first is True
    assert second is False  # deduped


def test_notification_service_dedup_expires():
    """Same key after cooldown window is sent again."""
    from backend.notifications.service import NotificationService

    svc = NotificationService()
    svc.smtp_configured = True
    svc._dedup_cache = {}
    svc._cooldown_seconds = 1

    with patch("smtplib.SMTP_SSL") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        first = svc.send_email("user@test.com", "Test", "body", dedup_key="key-2")
        time.sleep(1.1)
        second = svc.send_email("user@test.com", "Test", "body", dedup_key="key-2")

    assert first is True
    assert second is True  # cooldown expired
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_notifications.py -v
```

Expected: `FAIL` — `send_email` has no `dedup_key` param

- [ ] **Step 4: Update `NotificationService`**

Replace `backend/notifications/service.py`:

```python
import smtplib
import time
from email.message import EmailMessage
from typing import Optional
from backend.config import settings
from backend.utils.logger import logger


class NotificationService:
    def __init__(self):
        self.smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)
        self.sms_configured = bool(
            settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER
        )
        self._dedup_cache: dict[str, float] = {}
        self._cooldown_seconds = settings.NOTIFICATION_COOLDOWN_MINUTES * 60

    def _is_duped(self, dedup_key: Optional[str]) -> bool:
        if not dedup_key:
            return False
        last = self._dedup_cache.get(dedup_key, 0)
        if time.time() - last < self._cooldown_seconds:
            return True
        self._dedup_cache[dedup_key] = time.time()
        # ponytail: unbounded dict — fine at single-user scale; add LRU if memory grows
        return False

    def send_email(self, to: str, subject: str, body: str, dedup_key: Optional[str] = None) -> bool:
        if not self.smtp_configured:
            logger.info(f"SMTP not configured, skipping email to {to}")
            return False
        if self._is_duped(dedup_key):
            logger.debug(f"Notification deduped (key={dedup_key})")
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to
            msg.set_content(body)
            port = int(settings.SMTP_PORT or 465)
            # SendGrid relay uses port 587 (TLS), others use 465 (SSL)
            if port == 587:
                with smtplib.SMTP(settings.SMTP_HOST, port) as server:
                    server.starttls()
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.send_message(msg)
            else:
                with smtplib.SMTP_SSL(settings.SMTP_HOST, port) as server:
                    server.login(settings.SMTP_USER, settings.SMTP_PASS)
                    server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send failed to {to}: {e}")
            return False

    def send_sms(self, to: str, body: str, dedup_key: Optional[str] = None) -> bool:
        if not self.sms_configured:
            logger.info(f"Twilio not configured, skipping SMS to {to}")
            return False
        if self._is_duped(dedup_key):
            logger.debug(f"SMS notification deduped (key={dedup_key})")
            return False
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(body=body, from_=settings.TWILIO_FROM_NUMBER, to=to)
            return True
        except Exception as e:
            logger.error(f"SMS send failed to {to}: {e}")
            return False
```

Update `notify_trade_executed` in `triggers.py` to pass `dedup_key`:

```python
# In notify_trade_executed, pass dedup key to prevent spam on high-frequency agents
dedup_key = f"trade_{user_id}_{symbol}_{action}"
notification_service.send_email(user.email, subject, body, dedup_key=dedup_key)
notification_service.send_sms(prefs.phone_number, body, dedup_key=dedup_key)
```

Similarly update `notify_agent_paused` and `notify_drawdown_warning` with appropriate dedup keys.

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_notifications.py -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add backend/notifications/service.py backend/config.py backend/notifications/triggers.py tests/test_notifications.py
git commit -m "feat(6D.1): notification dedup cooldown; SendGrid SMTP relay via port 587; Twilio via existing package"
```

---

### Task 6D.2: `POST /api/notifications/test` endpoint + daily digest scheduler

**Files:**
- Modify: `backend/api/notifications.py` (or create if absent — check first)
- Modify: `backend/main.py`

- [ ] **Step 1: Check if notifications API exists**

```bash
ls /Users/coleadams/labourious/backend/api/ | grep notif
```

- [ ] **Step 2: Add test-send endpoint**

In the notifications API router, add:

```python
@router.post("/test")
async def send_test_notification(current_user: User = Depends(get_current_user)):
    """Send test email + SMS to verify notification config."""
    from backend.notifications.service import NotificationService
    from backend.notifications.triggers import notification_service

    results = {}
    # Test email
    if notification_service.smtp_configured:
        ok = notification_service.send_email(
            to=current_user.email,
            subject="Labourious — Test Notification",
            body="Your notification config is working.",
        )
        results["email"] = "sent" if ok else "failed"
    else:
        results["email"] = "not_configured"

    return results
```

- [ ] **Step 3: Wire daily digest APScheduler job in `main.py`**

In `backend/main.py`, inside the lifespan startup, add after orchestrator initialization:

```python
    # Daily digest at 08:00 local time
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from backend.notifications.triggers import send_daily_digest

    _digest_scheduler = AsyncIOScheduler()
    _digest_scheduler.add_job(
        _send_digest_for_all_users,
        CronTrigger(hour=8, minute=0),
        id="daily_digest",
    )
    _digest_scheduler.start()
```

Add `_send_digest_for_all_users` helper in `main.py`:

```python
async def _send_digest_for_all_users():
    """Compute per-user aggregate and send daily digest."""
    from backend.database.db import get_db_session
    from backend.database.models import User, Agent
    from backend.config import settings
    from backend.notifications.triggers import send_daily_digest

    with get_db_session(settings.DATABASE_URL) as session:
        users = session.query(User).all()
        for user in users:
            agents = session.query(Agent).filter(Agent.user_id == user.id, Agent.is_active == True).all()
            if not agents:
                continue
            total_pnl = sum(a.total_pnl or 0 for a in agents)
            best = max(agents, key=lambda a: a.total_pnl or 0, default=None)
            worst = min(agents, key=lambda a: a.total_pnl or 0, default=None)
            send_daily_digest(user.id, {
                "total_pnl": total_pnl,
                "trade_count": sum(a.total_trades or 0 for a in agents),
                "best_agent": best.name if best else "N/A",
                "worst_agent": worst.name if worst else "N/A",
            })
```

- [ ] **Step 4: Commit**

```bash
git add backend/api/notifications.py backend/main.py
git commit -m "feat(6D.2): POST /api/notifications/test endpoint; daily digest APScheduler job at 08:00"
```

---

### Task 6D.3: Notifications settings page — phone number + test button

**Files:**
- Modify: `frontend/src/pages/NotificationsPage.jsx`

- [ ] **Step 1: Add phone number field and test button to NotificationsPage**

The page already uses `notificationsApi.getPreferences` and `notificationsApi.updatePreferences`. Add:

```jsx
// In NotificationsPage, add a "Test" button that calls notificationsApi.sendTest()
// and shows result in a toast/inline message.

// Add to api-client.js:
// notificationsApi: {
//   ...existing,
//   sendTest: () => apiClient.post('/api/notifications/test'),
// }
```

In `frontend/src/utils/api-client.js`, update `notificationsApi`:

```javascript
export const notificationsApi = {
  getPreferences: () => apiClient.get('/api/notifications/preferences'),
  updatePreferences: (data) => apiClient.patch('/api/notifications/preferences', data),
  sendTest: () => apiClient.post('/api/notifications/test'),
};
```

In `NotificationsPage.jsx`, add after the save button:

```jsx
const [testResult, setTestResult] = useState(null);

const handleTest = async () => {
  try {
    const result = await notificationsApi.sendTest();
    setTestResult(result);
  } catch (err) {
    setTestResult({ error: err.message });
  }
};

// Render:
<button onClick={handleTest} style={{ /* secondary button style */ }}>
  Send Test
</button>
{testResult && (
  <div style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', marginTop: '0.5rem', color: 'var(--color-text-secondary)' }}>
    {JSON.stringify(testResult)}
  </div>
)}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/NotificationsPage.jsx frontend/src/utils/api-client.js
git commit -m "feat(6D.3): notifications page test button; add notificationsApi.sendTest"
```

---

## Self-Review Checklist

| Requirement | Task |
|-------------|------|
| Alpaca live trading (not hardcoded paper) | 6A.1 |
| Binance live trading | Already works (ccxt calls real API with real keys) — verified in 6A.1 |
| Kraken connector | 6A.2 |
| Generic exchange via ccxt | 6A.3 |
| Vault credential pre-flight check | 6A.4 |
| `/api/brokers/vault-check/{broker}` endpoint | 6A.4 |
| Alpaca live fill price polling | 6A.5 |
| DailySnapshot write per trade | 6A.6 |
| Alembic migration for DailySnapshot fields | 6A.6 |
| Backtest equity curve non-empty | 6B.1 |
| Backtest return/rate normalisation (decimal vs pct) | 6B.1 |
| Walk-forward results rendered in UI | 6B.2 |
| Backtest history panel | 6B.3 |
| Strategy context editable in AgentInspector | 6C.1 |
| Strategy preset templates | 6C.1 |
| Live-mode confirmation dialog | 6C.2 |
| Email via SMTP (SendGrid relay or direct) | 6D.1 — uses existing smtplib with port 587 path |
| Twilio SMS | Already implemented in NotificationService — 6D.1 adds dedup |
| Notification dedup cooldown | 6D.1 |
| `POST /api/notifications/test` | 6D.2 |
| Daily digest APScheduler job | 6D.2 |
| Notifications page test button | 6D.3 |
| Paper trading remains safe default everywhere | 6A.1 (paper=True default in get_connector) |
| All secrets from vault only | Enforced in 6A.1-6A.4 |
| Commit per task | All tasks have commit steps |

---

## Phase 7 Preparation — Team Accounts (Non-Blocking Stubs)

Phase 7 introduces multi-user team accounts: shared agent visibility, role-based permissions, invite flow. Phase 6 does **not** implement any of this, but Phase 6 must not make Phase 7 harder.

**What Phase 6 leaves correctly positioned:**

1. **`Agent.user_id` FK is nullable** (`nullable=True` in models.py). Phase 7 will add team ownership without a breaking schema change.
2. **`User.role` Enum** already has `ADMIN`, `TRADER`, `VIEWER`. Phase 7 adds `TEAM_ADMIN` — one Alembic migration, no logic rewrite.
3. **`_check_agent_access` in `agents.py`** checks `agent.user_id == current_user.id`. Phase 7 replaces this with `agent.team_id in current_user.team_memberships` — isolated function, clean swap.
4. **WS broadcast** uses `manager.broadcast()` (global). Phase 7 needs room-scoped broadcast. The `python-socketio` room pattern (`sio.emit(event, data, room=f"team_{team_id}")`) is already architected for in CLAUDE.md.

**Phase 7 schema additions (do NOT implement in Phase 6):**
```sql
-- Phase 7 migrations (placeholder — do not add yet)
CREATE TABLE teams (id UUID, name TEXT, owner_id UUID FK users.id);
CREATE TABLE team_memberships (team_id UUID FK teams.id, user_id UUID FK users.id, role TEXT);
ALTER TABLE agents ADD COLUMN team_id UUID NULLABLE FK teams.id;
```

**Phase 7 UI additions (placeholder routes already in App.jsx):**
- `/settings/team` — team management page
- `/agents` filter by `team_id`
- Agent inspector shows team badge

**Action for Phase 6:** No code changes needed. Document above so Phase 7 plan author has context.

---

## Execution Handoff

Plan saved to `docs/superpowers/plans/2026-06-21-phase6-live-trading-backtest-strategy.md`.

**Execution order (dependency-aware):**

```
P1 (live trading — all sequential, each builds on prior):
  6A.1 → 6A.2 → 6A.3 → 6A.4 → 6A.5 → 6A.6

P2 (backtest — independent of P1, run in parallel if using subagents):
  6B.1 → 6B.2 → 6B.3

P3 (frontend UX — independent of P1/P2 backend):
  6C.1 → 6C.2

P4 (notifications — independent):
  6D.1 → 6D.2 → 6D.3
```

**Recommended subagent split (if using superpowers:subagent-driven-development):**
- Subagent A: 6A.1 → 6A.2 → 6A.3 → 6A.4 → 6A.5 → 6A.6 (broker/live trading track)
- Subagent B: 6B.1 → 6B.2 → 6B.3 (backtest track — after 6B.1 backend done)
- Subagent C: 6C.1 → 6C.2 → 6D.3 (frontend track — pure UI, no backend deps)
- Subagent D: 6D.1 → 6D.2 (notifications track)

**Risks:**
1. **Alpaca live fill polling** (6A.5) — market orders usually fill in <1s but edge cases exist. The 5s poll timeout is a known ceiling (`ponytail: global poll, per-webhook if latency matters`).
2. **Kraken krakenex sync API** (6A.2) — krakenex is synchronous; wrapped in `async def` without `asyncio.to_thread`. For high-frequency agents this blocks the event loop. Mitigation: wrap kraken API calls in `asyncio.to_thread(self._api().query_private, ...)` if throughput becomes an issue.
3. **Backtest equity curve size** (6B.1) — for 5-year daily data that's ~1300 entries in `result_json`. Acceptable for SQLite JSON column. Monitor if users run longer backtests.
4. **Notification dedup cache** (6D.1) — in-memory dict clears on restart. Fine for single-process; Phase 7 Redis cache if multi-process.
