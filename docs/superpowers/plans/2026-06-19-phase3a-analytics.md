# Phase 3A — Advanced Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Analytics page with equity curve, agent leaderboard, correlation matrix, attribution waterfall, and backtest runner — backed by a daily snapshot engine and REST API.

**Architecture:** An APScheduler EOD job writes one `daily_snapshots` row per agent at market close; API endpoints read from that table for fast chart queries; today's live metrics are computed fresh from the `trades` table. Frontend is a single-scroll `AnalyticsPage.jsx` using Recharts for all charts.

**Tech Stack:** Python/FastAPI/SQLAlchemy/APScheduler (backend), React 18/Recharts 2.12/Zustand 5/Framer Motion (frontend), Alembic (migrations), pytest (tests).

## Global Constraints

- Python ≥ 3.11, FastAPI, SQLAlchemy async sessions via `get_db_session(settings.DATABASE_URL)` — same pattern as `backend/api/dashboard.py`
- All new API routers registered in `backend/main.py` with `app.include_router()`
- No new npm dependencies — Recharts 2.12.7 already installed
- CSS uses only existing vars from `frontend/src/styles/index.css` — `--color-accent-primary` (#00ff88), `--color-accent-secondary` (#00d4ff), `--color-accent-warning` (#ffb020), `--color-accent-danger` (#ff4444), `--color-bg-card`, `--color-border`, `--font-mono`
- Color note from design choices: body text uses `--color-text-primary` (#e8e8f0) not hacker-green; positive P&L = `--color-pnl-positive`, negative = `--color-pnl-negative`
- All design choices frozen in `docs/superpowers/specs/2026-06-19-phase3-frontend-design-choices.md` — do not re-derive
- No API keys in logs. `get_db_session` context manager already handles session teardown.
- Alembic: generate migration with `alembic revision --autogenerate -m "description"`, apply with `alembic upgrade head`
- Frontend API calls go through `apiClient` from `frontend/src/utils/api-client.js` (axios instance, base URL from constants, auto-normalises errors)
- Tests: `pytest tests/ -v --asyncio-mode=auto`. Test client fixture in `tests/conftest.py`: `client` (session-scoped TestClient wrapping `backend.main:app`)

---

## File Map

### New backend files
| File | Responsibility |
|---|---|
| `backend/analytics/__init__.py` | package marker |
| `backend/analytics/metrics.py` | Pure functions: `compute_sharpe`, `compute_max_drawdown`, `compute_correlation_matrix`, `compute_attribution` |
| `backend/analytics/snapshot_job.py` | APScheduler EOD job — reads trades, calls metrics, writes `daily_snapshots` |
| `backend/api/analytics.py` | GET endpoints: `/api/analytics/portfolio`, `/equity-curve`, `/leaderboard`, `/correlation`, `/attribution` |
| `backend/api/backtest_ui.py` | POST `/api/backtest/run`, GET `/api/backtest/{run_id}`, GET `/api/backtest/history` |

### New migration
| File | Responsibility |
|---|---|
| `alembic/versions/<hash>_phase3a_analytics_tables.py` | Add `daily_snapshots` + `backtest_results` tables |

### Modified backend files
| File | Change |
|---|---|
| `backend/database/models.py` | Add `DailySnapshot`, `BacktestResult` model classes |
| `backend/main.py` | Import + register `analytics_router`, `backtest_ui_router`; add snapshot_job to lifespan |

### New test files
| File | Responsibility |
|---|---|
| `tests/test_metrics.py` | Unit tests for all pure metric functions |
| `tests/test_snapshot_job.py` | Mock DB — verify snapshot written correctly |
| `tests/test_analytics_api.py` | Mock DB — verify all analytics endpoints |
| `tests/test_backtest_ui.py` | Mock backtest script — verify run/poll lifecycle |

### New frontend files
| File | Responsibility |
|---|---|
| `frontend/src/pages/AnalyticsPage.jsx` | Single-scroll page, composes all analytics sections |
| `frontend/src/components/Analytics/EquityChart.jsx` | Recharts LineChart, 30d equity curve |
| `frontend/src/components/Analytics/AgentLeaderboard.jsx` | Sortable table with inline bar |
| `frontend/src/components/Analytics/CorrelationMatrix.jsx` | Numbers table, amber flag >0.7 |
| `frontend/src/components/Analytics/AttributionWaterfall.jsx` | Recharts BarChart waterfall |
| `frontend/src/components/Analytics/BacktestRunner.jsx` | Inline form + results panel |
| `frontend/src/stores/analytics.store.js` | Zustand store for all analytics data |

### Modified frontend files
| File | Change |
|---|---|
| `frontend/src/App.jsx` | Add `/analytics` route + `◈ Analytics` nav item |
| `frontend/src/utils/api-client.js` | Add `analyticsApi` and `backtestApi` named exports |

---

## Task 1: DB Models + Migration

**Files:**
- Modify: `backend/database/models.py`
- Create: `alembic/versions/<hash>_phase3a_analytics_tables.py` (generated)

**Interfaces:**
- Produces: `DailySnapshot` model (fields: `id`, `agent_id`, `date`, `total_pnl`, `daily_return_pct`, `sharpe_ratio`, `max_drawdown`, `win_rate`, `trade_count`); `BacktestResult` model (fields: `id`, `agent_id`, `run_at`, `start_date`, `end_date`, `mode`, `status`, `result_json`)

- [ ] **Step 1: Add models to `backend/database/models.py`**

Open `backend/database/models.py`. At the end of the file, after the `PendingApproval` class, add:

```python
from datetime import date as date_type  # add to top-level imports


class DailySnapshot(Base):
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    date = Column(String(10), nullable=False)          # ISO date string "YYYY-MM-DD"
    total_pnl = Column(Float, nullable=False, default=0.0)
    daily_return_pct = Column(Float, nullable=False, default=0.0)
    sharpe_ratio = Column(Float, nullable=True)        # NULL until 30 days of data
    max_drawdown = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)
    trade_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # ponytail: no UNIQUE constraint here — enforced in snapshot_job via upsert logic
    agent = relationship("Agent", backref="snapshots")


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(String(36), primary_key=True)          # UUID string
    agent_id = Column(Integer, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    run_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    start_date = Column(String(10), nullable=False)    # "YYYY-MM-DD"
    end_date = Column(String(10), nullable=False)
    mode = Column(String(20), nullable=False, default="basic")  # "basic" | "walk_forward"
    status = Column(String(20), nullable=False, default="running")  # "running" | "done" | "failed"
    result_json = Column(JSON, nullable=True)          # NULL until done

    agent = relationship("Agent", backref="backtest_results")
```

- [ ] **Step 2: Generate migration**

```bash
alembic revision --autogenerate -m "phase3a_analytics_tables"
```

Expected: new file created at `alembic/versions/<hash>_phase3a_analytics_tables.py` containing `op.create_table("daily_snapshots", ...)` and `op.create_table("backtest_results", ...)`.

- [ ] **Step 3: Apply migration**

```bash
alembic upgrade head
```

Expected: `INFO  [alembic.runtime.migration] Running upgrade ... -> <hash>, phase3a_analytics_tables`

- [ ] **Step 4: Verify tables exist**

```bash
python3 -c "
from backend.database.db import get_db_session
from backend.config import settings
from backend.database.models import DailySnapshot, BacktestResult
from sqlalchemy import select
with get_db_session(settings.DATABASE_URL) as s:
    s.execute(select(DailySnapshot).limit(1))
    s.execute(select(BacktestResult).limit(1))
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/database/models.py alembic/versions/
git commit -m "feat: add DailySnapshot and BacktestResult models + migration"
```

---

## Task 2: Pure Metrics Functions

**Files:**
- Create: `backend/analytics/__init__.py`
- Create: `backend/analytics/metrics.py`
- Create: `tests/test_metrics.py`

**Interfaces:**
- Produces:
  - `compute_sharpe(daily_returns: list[float], risk_free_rate: float = 0.0) -> float`
  - `compute_max_drawdown(equity_curve: list[float]) -> float` — returns negative float (e.g. -0.083)
  - `compute_correlation_matrix(agents_daily_returns: dict[str, list[float]]) -> dict[str, dict[str, float]]`
  - `compute_attribution(trades: list[dict], date_str: str) -> dict[str, float]` — `trades` are dicts with keys `agent_id`, `pnl`, `closed_at` (ISO string); returns `{str(agent_id): pct_contribution}`

- [ ] **Step 1: Write failing tests**

Create `tests/test_metrics.py`:

```python
import math
import pytest
from backend.analytics.metrics import (
    compute_sharpe,
    compute_max_drawdown,
    compute_correlation_matrix,
    compute_attribution,
)


def test_compute_sharpe_positive():
    returns = [0.01, 0.02, -0.005, 0.015, 0.008] * 10  # 50 data points
    result = compute_sharpe(returns)
    assert isinstance(result, float)
    assert result > 0


def test_compute_sharpe_zero_std():
    # All same return → std=0 → sharpe=0.0
    returns = [0.01] * 30
    assert compute_sharpe(returns) == 0.0


def test_compute_sharpe_empty():
    assert compute_sharpe([]) == 0.0


def test_compute_max_drawdown_basic():
    # Equity goes 100 → 150 → 90 — drawdown = (90-150)/150 = -0.4
    equity = [100.0, 120.0, 150.0, 130.0, 90.0]
    dd = compute_max_drawdown(equity)
    assert dd < 0
    assert abs(dd - (-0.4)) < 0.001


def test_compute_max_drawdown_no_drawdown():
    equity = [100.0, 110.0, 120.0, 130.0]
    assert compute_max_drawdown(equity) == 0.0


def test_compute_max_drawdown_empty():
    assert compute_max_drawdown([]) == 0.0


def test_compute_correlation_matrix_identical():
    # Same series → correlation = 1.0
    data = {"A": [1.0, 2.0, 3.0, 4.0], "B": [1.0, 2.0, 3.0, 4.0]}
    result = compute_correlation_matrix(data)
    assert abs(result["A"]["B"] - 1.0) < 0.001
    assert abs(result["B"]["A"] - 1.0) < 0.001


def test_compute_correlation_matrix_uncorrelated():
    import random
    random.seed(42)
    data = {
        "A": [1.0, -1.0, 1.0, -1.0, 1.0, -1.0],
        "B": [1.0,  1.0, 1.0,  1.0, 1.0,  1.0],
    }
    result = compute_correlation_matrix(data)
    assert abs(result["A"]["B"]) < 0.1


def test_compute_correlation_matrix_single_agent():
    data = {"A": [0.01, 0.02, -0.01]}
    result = compute_correlation_matrix(data)
    assert result == {}  # no pairs


def test_compute_attribution_sums_to_100():
    trades = [
        {"agent_id": 1, "pnl": 420.0,  "closed_at": "2026-06-19T15:00:00"},
        {"agent_id": 2, "pnl": 210.0,  "closed_at": "2026-06-19T14:00:00"},
        {"agent_id": 3, "pnl": -85.0,  "closed_at": "2026-06-19T12:00:00"},
    ]
    result = compute_attribution(trades, "2026-06-19")
    # sum of abs pct contributions = 100
    total = sum(abs(v) for v in result.values())
    assert abs(total - 100.0) < 0.01


def test_compute_attribution_empty():
    assert compute_attribution([], "2026-06-19") == {}


def test_compute_attribution_filters_by_date():
    trades = [
        {"agent_id": 1, "pnl": 100.0, "closed_at": "2026-06-19T15:00:00"},
        {"agent_id": 2, "pnl": 200.0, "closed_at": "2026-06-18T15:00:00"},  # different day
    ]
    result = compute_attribution(trades, "2026-06-19")
    assert "1" in result
    assert "2" not in result
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_metrics.py -v 2>&1 | head -20
```

Expected: `ImportError` or `ModuleNotFoundError: No module named 'backend.analytics'`

- [ ] **Step 3: Create package + implement**

Create `backend/analytics/__init__.py` (empty).

Create `backend/analytics/metrics.py`:

```python
import math
from typing import Optional


def compute_sharpe(daily_returns: list[float], risk_free_rate: float = 0.0) -> float:
    if len(daily_returns) < 2:
        return 0.0
    n = len(daily_returns)
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    std = math.sqrt(variance)
    if std == 0.0:
        return 0.0
    return round((mean - risk_free_rate) / std * math.sqrt(252), 4)


def compute_max_drawdown(equity_curve: list[float]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve[1:]:
        if value > peak:
            peak = value
        dd = (value - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 6)


def compute_correlation_matrix(
    agents_daily_returns: dict[str, list[float]]
) -> dict[str, dict[str, float]]:
    agents = list(agents_daily_returns.keys())
    if len(agents) < 2:
        return {}

    def pearson(xs: list[float], ys: list[float]) -> float:
        n = min(len(xs), len(ys))
        if n < 2:
            return 0.0
        xs, ys = xs[:n], ys[:n]
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        if dx == 0 or dy == 0:
            return 0.0
        return round(num / (dx * dy), 4)

    result: dict[str, dict[str, float]] = {}
    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i >= j:
                continue
            corr = pearson(agents_daily_returns[a], agents_daily_returns[b])
            result.setdefault(a, {})[b] = corr
            result.setdefault(b, {})[a] = corr
    return result


def compute_attribution(
    trades: list[dict], date_str: str
) -> dict[str, float]:
    day_trades = [
        t for t in trades
        if t.get("closed_at", "")[:10] == date_str and t.get("pnl") is not None
    ]
    if not day_trades:
        return {}

    total_gross = sum(abs(t["pnl"]) for t in day_trades)
    if total_gross == 0.0:
        return {}

    result: dict[str, float] = {}
    for t in day_trades:
        key = str(t["agent_id"])
        pct = round((t["pnl"] / total_gross) * 100, 2)
        result[key] = result.get(key, 0.0) + pct
    return result
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_metrics.py -v
```

Expected: all 11 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/ tests/test_metrics.py
git commit -m "feat: add pure analytics metric functions with tests"
```

---

## Task 3: Snapshot Job

**Files:**
- Create: `backend/analytics/snapshot_job.py`
- Create: `tests/test_snapshot_job.py`

**Interfaces:**
- Consumes: `compute_sharpe`, `compute_max_drawdown` from `backend.analytics.metrics`; `DailySnapshot`, `Agent`, `Trade` from `backend.database.models`; `get_db_session` from `backend.database.db`
- Produces: `run_eod_snapshot(database_url: str) -> None` — called by APScheduler

- [ ] **Step 1: Write failing test**

Create `tests/test_snapshot_job.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, date


def make_mock_agent(agent_id: int, total_pnl: float = 500.0):
    agent = MagicMock()
    agent.id = agent_id
    agent.total_pnl = total_pnl
    agent.paper_trading_balance = 100000.0
    return agent


def make_mock_trade(agent_id: int, pnl: float, is_win: bool):
    trade = MagicMock()
    trade.agent_id = agent_id
    trade.pnl = pnl
    trade.closed_at = datetime(2026, 6, 19, 15, 0, 0)
    return trade


def test_run_eod_snapshot_writes_row(tmp_path):
    db_url = f"sqlite:///{tmp_path}/test.db"

    # Bootstrap real tables
    from backend.database.db import init_db, get_db_session
    from backend.database.models import Agent, AgentStatus, AgentType, DailySnapshot
    from sqlalchemy import select

    init_db(db_url)

    with get_db_session(db_url) as session:
        agent = Agent(
            name="TestAgent",
            agent_type=AgentType.CUSTOM,
            symbol="BTC/USD",
            total_pnl=500.0,
            total_trades=5,
            winning_trades=3,
        )
        session.add(agent)
        session.commit()
        agent_id = agent.id

    from backend.analytics.snapshot_job import run_eod_snapshot
    run_eod_snapshot(db_url)

    with get_db_session(db_url) as session:
        snapshots = session.execute(
            select(DailySnapshot).where(DailySnapshot.agent_id == agent_id)
        ).scalars().all()

    assert len(snapshots) == 1
    assert snapshots[0].total_pnl == 500.0
    assert snapshots[0].trade_count == 5


def test_run_eod_snapshot_idempotent(tmp_path):
    """Running twice on same day should not duplicate rows."""
    db_url = f"sqlite:///{tmp_path}/test.db"

    from backend.database.db import init_db, get_db_session
    from backend.database.models import Agent, AgentType, DailySnapshot
    from sqlalchemy import select

    init_db(db_url)

    with get_db_session(db_url) as session:
        agent = Agent(name="TestAgent2", agent_type=AgentType.CUSTOM, symbol="ETH/USD")
        session.add(agent)
        session.commit()

    from backend.analytics.snapshot_job import run_eod_snapshot
    run_eod_snapshot(db_url)
    run_eod_snapshot(db_url)

    with get_db_session(db_url) as session:
        count = session.execute(select(DailySnapshot)).scalars().all()

    assert len(count) == 1
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_snapshot_job.py -v 2>&1 | head -15
```

Expected: `ImportError: cannot import name 'run_eod_snapshot'`

- [ ] **Step 3: Implement snapshot job**

Create `backend/analytics/snapshot_job.py`:

```python
"""APScheduler EOD job — writes one DailySnapshot row per agent."""
from datetime import datetime, date
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Agent, Trade, DailySnapshot, TradeStatus
from backend.analytics.metrics import compute_sharpe, compute_max_drawdown
from backend.utils.logger import setup_logger

logger = setup_logger("snapshot_job")


def run_eod_snapshot(database_url: str) -> None:
    today = date.today().isoformat()
    logger.info(f"Running EOD snapshot for {today}")

    with get_db_session(database_url) as session:
        agents = session.execute(select(Agent)).scalars().all()

        for agent in agents:
            # Skip if row already exists for today (idempotent)
            existing = session.execute(
                select(DailySnapshot)
                .where(DailySnapshot.agent_id == agent.id)
                .where(DailySnapshot.date == today)
            ).scalar_one_or_none()
            if existing:
                continue

            # Closed trades for this agent (all time — for rolling metrics)
            trades = session.execute(
                select(Trade)
                .where(Trade.agent_id == agent.id)
                .where(Trade.status == TradeStatus.CLOSED)
                .where(Trade.pnl.isnot(None))
            ).scalars().all()

            trade_count = len(trades)
            wins = sum(1 for t in trades if (t.pnl or 0) > 0)
            win_rate = round((wins / trade_count * 100), 2) if trade_count else 0.0

            # Daily return pct relative to paper_trading_balance baseline
            baseline = agent.paper_trading_balance or 100_000.0
            daily_return_pct = round((agent.total_pnl / baseline) * 100, 4) if baseline else 0.0

            # Sharpe from last 30 snapshots (rolling)
            past_snapshots = session.execute(
                select(DailySnapshot)
                .where(DailySnapshot.agent_id == agent.id)
                .order_by(DailySnapshot.date.desc())
                .limit(29)
            ).scalars().all()

            rolling_returns = [s.daily_return_pct for s in past_snapshots] + [daily_return_pct]
            sharpe = compute_sharpe(rolling_returns) if len(rolling_returns) >= 10 else None

            # Equity curve from snapshots for drawdown
            equity = [baseline + (s.total_pnl or 0) for s in reversed(past_snapshots)]
            equity.append(baseline + agent.total_pnl)
            max_dd = compute_max_drawdown(equity) if len(equity) >= 2 else None

            snapshot = DailySnapshot(
                agent_id=agent.id,
                date=today,
                total_pnl=round(agent.total_pnl, 4),
                daily_return_pct=daily_return_pct,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                win_rate=win_rate,
                trade_count=trade_count,
            )
            session.add(snapshot)

        session.commit()
    logger.info(f"EOD snapshot complete for {today}")
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_snapshot_job.py -v
```

Expected: both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/analytics/snapshot_job.py tests/test_snapshot_job.py
git commit -m "feat: add EOD snapshot job with idempotent upsert logic"
```

---

## Task 4: Analytics REST API

**Files:**
- Create: `backend/api/analytics.py`
- Create: `tests/test_analytics_api.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `DailySnapshot`, `Agent`, `Trade` models; `compute_correlation_matrix`, `compute_attribution` from `backend.analytics.metrics`
- Produces: router at prefix `/api/analytics`, endpoints: `GET /portfolio`, `GET /equity-curve`, `GET /leaderboard`, `GET /correlation`, `GET /attribution`

- [ ] **Step 1: Write failing tests**

Create `tests/test_analytics_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_portfolio_endpoint_returns_200():
    response = client.get("/api/analytics/portfolio")
    assert response.status_code == 200
    data = response.json()
    assert "total_pnl" in data
    assert "sharpe_ratio" in data
    assert "max_drawdown" in data
    assert "win_rate" in data
    assert "return_30d_pct" in data


def test_equity_curve_default_days():
    response = client.get("/api/analytics/equity-curve")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_equity_curve_custom_days():
    response = client.get("/api/analytics/equity-curve?days=7")
    assert response.status_code == 200


def test_leaderboard_returns_list():
    response = client.get("/api/analytics/leaderboard")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_leaderboard_sort_by_sharpe():
    response = client.get("/api/analytics/leaderboard?sort_by=sharpe")
    assert response.status_code == 200


def test_correlation_returns_dict():
    response = client.get("/api/analytics/correlation")
    assert response.status_code == 200
    assert isinstance(response.json(), dict)


def test_attribution_today():
    response = client.get("/api/analytics/attribution")
    assert response.status_code == 200
    data = response.json()
    assert "date" in data
    assert "contributions" in data


def test_attribution_specific_date():
    response = client.get("/api/analytics/attribution?date=2026-06-19")
    assert response.status_code == 200
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_analytics_api.py -v 2>&1 | head -15
```

Expected: `404 Not Found` (routes not registered yet)

- [ ] **Step 3: Implement router**

Create `backend/api/analytics.py`:

```python
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Agent, Trade, DailySnapshot, TradeStatus
from backend.analytics.metrics import compute_correlation_matrix, compute_attribution
from backend.config import settings

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/portfolio")
async def get_portfolio_summary():
    """Portfolio-level summary: total P&L, rolling Sharpe, max drawdown, win rate."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        if not agents:
            return {
                "total_pnl": 0.0, "sharpe_ratio": None, "max_drawdown": None,
                "win_rate": 0.0, "return_30d_pct": 0.0, "agent_count": 0,
            }

        total_pnl = sum(a.total_pnl for a in agents)
        total_trades = sum(a.total_trades for a in agents)
        total_wins = sum(a.winning_trades for a in agents)
        win_rate = round((total_wins / total_trades * 100), 1) if total_trades else 0.0

        # Last 30 days: sum daily_return_pct across all agents
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        snapshots = session.execute(
            select(DailySnapshot)
            .where(DailySnapshot.date >= cutoff)
            .order_by(DailySnapshot.date)
        ).scalars().all()

        # Aggregate by date
        by_date: dict[str, float] = {}
        for s in snapshots:
            by_date[s.date] = by_date.get(s.date, 0.0) + (s.daily_return_pct or 0.0)
        daily_returns = list(by_date.values())

        from backend.analytics.metrics import compute_sharpe, compute_max_drawdown
        sharpe = compute_sharpe(daily_returns) if len(daily_returns) >= 10 else None
        equity = [100.0 + sum(daily_returns[:i+1]) for i in range(len(daily_returns))]
        max_dd = compute_max_drawdown(equity) if len(equity) >= 2 else None
        return_30d = round(sum(daily_returns), 2) if daily_returns else 0.0

        return {
            "total_pnl": round(total_pnl, 2),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "return_30d_pct": return_30d,
            "agent_count": len(agents),
        }


@router.get("/equity-curve")
async def get_equity_curve(
    days: int = Query(default=30, ge=1, le=365),
    agent_id: Optional[int] = Query(default=None),
):
    """Daily equity data for chart. agent_id=None means portfolio total."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        q = select(DailySnapshot).where(DailySnapshot.date >= cutoff).order_by(DailySnapshot.date)
        if agent_id is not None:
            q = q.where(DailySnapshot.agent_id == agent_id)
        snapshots = session.execute(q).scalars().all()

    if agent_id is not None:
        return [{"date": s.date, "pnl": s.total_pnl, "return_pct": s.daily_return_pct} for s in snapshots]

    # Aggregate portfolio by date
    by_date: dict[str, float] = {}
    for s in snapshots:
        by_date[s.date] = by_date.get(s.date, 0.0) + (s.total_pnl or 0.0)
    return [{"date": d, "pnl": round(p, 2)} for d, p in sorted(by_date.items())]


@router.get("/leaderboard")
async def get_leaderboard(sort_by: str = Query(default="return", enum=["return", "sharpe", "win_rate", "trades"])):
    """All agents sorted by chosen metric."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()

        # Pull latest snapshot per agent
        latest: dict[int, DailySnapshot] = {}
        for agent in agents:
            snap = session.execute(
                select(DailySnapshot)
                .where(DailySnapshot.agent_id == agent.id)
                .order_by(DailySnapshot.date.desc())
                .limit(1)
            ).scalar_one_or_none()
            if snap:
                latest[agent.id] = snap

    rows = []
    for a in agents:
        snap = latest.get(a.id)
        rows.append({
            "id": a.id,
            "name": a.name,
            "room": a.room,
            "total_pnl": round(a.total_pnl, 2),
            "return_pct": snap.daily_return_pct if snap else 0.0,
            "sharpe_ratio": snap.sharpe_ratio if snap else None,
            "max_drawdown": snap.max_drawdown if snap else None,
            "win_rate": round(a.win_rate, 1),
            "total_trades": a.total_trades,
            "confidence_score": a.confidence_score,
            "status": a.status.value,
        })

    sort_key = {
        "return": lambda r: r["total_pnl"],
        "sharpe": lambda r: r["sharpe_ratio"] or -999,
        "win_rate": lambda r: r["win_rate"],
        "trades": lambda r: r["total_trades"],
    }[sort_by]
    rows.sort(key=sort_key, reverse=True)
    return rows


@router.get("/correlation")
async def get_correlation():
    """Pairwise Pearson correlation of last 30d daily returns per agent."""
    cutoff = (date.today() - timedelta(days=30)).isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        agent_names = {a.id: a.name for a in agents}

        snapshots = session.execute(
            select(DailySnapshot)
            .where(DailySnapshot.date >= cutoff)
            .order_by(DailySnapshot.date)
        ).scalars().all()

    # Build {agent_name: [daily_return_pct, ...]} in date order
    by_agent: dict[str, list[float]] = {}
    for s in snapshots:
        name = agent_names.get(s.agent_id, str(s.agent_id))
        by_agent.setdefault(name, []).append(s.daily_return_pct or 0.0)

    return compute_correlation_matrix(by_agent)


@router.get("/attribution")
async def get_attribution(date_str: Optional[str] = Query(default=None, alias="date")):
    """Per-agent P&L contribution for a given date (default: today)."""
    target_date = date_str or date.today().isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        trades = session.execute(
            select(Trade)
            .where(Trade.status == TradeStatus.CLOSED)
            .where(Trade.pnl.isnot(None))
        ).scalars().all()

        agents = session.execute(select(Agent)).scalars().all()
        agent_names = {str(a.id): a.name for a in agents}

    trade_dicts = [
        {
            "agent_id": t.agent_id,
            "pnl": t.pnl,
            "closed_at": t.closed_at.isoformat() if t.closed_at else "",
        }
        for t in trades
    ]

    contributions = compute_attribution(trade_dicts, target_date)
    named = {agent_names.get(k, k): v for k, v in contributions.items()}

    return {
        "date": target_date,
        "contributions": named,   # {agent_name: pct_contribution}
    }
```

- [ ] **Step 4: Register router in `backend/main.py`**

In `backend/main.py`, add after the existing imports:

```python
from backend.api.analytics import router as analytics_router
```

And after the last `app.include_router(settings_router)` line:

```python
app.include_router(analytics_router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_analytics_api.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/analytics.py tests/test_analytics_api.py backend/main.py
git commit -m "feat: add analytics REST API with portfolio/equity/leaderboard/correlation/attribution endpoints"
```

---

## Task 5: Backtest UI API

**Files:**
- Create: `backend/api/backtest_ui.py`
- Create: `tests/test_backtest_ui.py`
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `BacktestResult` model; `backend.scripts.backtest` module (called via `asyncio.create_subprocess_exec`)
- Produces: router at prefix `/api/backtest`, endpoints: `POST /run`, `GET /{run_id}`, `GET /history`

- [ ] **Step 1: Write failing tests**

Create `tests/test_backtest_ui.py`:

```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_backtest_run_returns_run_id():
    response = client.post("/api/backtest/run", json={
        "agent_id": 999,   # non-existent, will be stored
        "start_date": "2024-01-01",
        "end_date": "2024-06-30",
        "mode": "basic",
    })
    assert response.status_code == 200
    data = response.json()
    assert "run_id" in data
    assert isinstance(data["run_id"], str)


def test_backtest_poll_returns_status():
    # Create a run first
    run_resp = client.post("/api/backtest/run", json={
        "agent_id": 999,
        "start_date": "2024-01-01",
        "end_date": "2024-03-31",
        "mode": "basic",
    })
    run_id = run_resp.json()["run_id"]
    # Poll it
    response = client.get(f"/api/backtest/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run_id
    assert data["status"] in ("running", "done", "failed")


def test_backtest_poll_unknown_id_returns_404():
    response = client.get("/api/backtest/nonexistent-id-abc")
    assert response.status_code == 404


def test_backtest_history_returns_list():
    response = client.get("/api/backtest/history")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_backtest_history_filter_by_agent():
    response = client.get("/api/backtest/history?agent_id=1")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

- [ ] **Step 2: Run to confirm failure**

```bash
pytest tests/test_backtest_ui.py -v 2>&1 | head -15
```

Expected: `404 Not Found`

- [ ] **Step 3: Implement router**

Create `backend/api/backtest_ui.py`:

```python
"""Backtest UI API — trigger, poll, history."""
import uuid
import asyncio
import json
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import BacktestResult
from backend.config import settings
from backend.utils.logger import setup_logger

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
logger = setup_logger("backtest_ui")


class BacktestRunRequest(BaseModel):
    agent_id: int
    start_date: str          # "YYYY-MM-DD"
    end_date: str            # "YYYY-MM-DD"
    mode: str = "basic"      # "basic" | "walk_forward"
    symbol: Optional[str] = None  # override; defaults to agent's symbol


@router.post("/run")
async def run_backtest(req: BacktestRunRequest):
    """Create a BacktestResult row (status=running), kick off subprocess, return run_id."""
    run_id = str(uuid.uuid4())

    with get_db_session(settings.DATABASE_URL) as session:
        result = BacktestResult(
            id=run_id,
            agent_id=req.agent_id,
            run_at=datetime.utcnow(),
            start_date=req.start_date,
            end_date=req.end_date,
            mode=req.mode,
            status="running",
        )
        session.add(result)
        session.commit()

    # Run backtest in background — don't await, returns immediately
    asyncio.create_task(_run_backtest_task(run_id, req))
    return {"run_id": run_id}


async def _run_backtest_task(run_id: str, req: BacktestRunRequest) -> None:
    """Background task — runs CLI, writes result to DB."""
    try:
        cmd = [
            sys.executable, "-m", "backend.scripts.backtest",
            "--start", req.start_date,
            "--end", req.end_date,
            "--mode", req.mode,
        ]
        if req.symbol:
            cmd += ["--symbol", req.symbol]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)

        if proc.returncode == 0:
            result_data = json.loads(stdout.decode())
            status = "done"
        else:
            result_data = {"error": stderr.decode()[:500]}
            status = "failed"

    except asyncio.TimeoutError:
        result_data = {"error": "backtest timed out after 120s"}
        status = "failed"
    except Exception as e:
        result_data = {"error": str(e)}
        status = "failed"

    with get_db_session(settings.DATABASE_URL) as session:
        row = session.execute(
            select(BacktestResult).where(BacktestResult.id == run_id)
        ).scalar_one_or_none()
        if row:
            row.status = status
            row.result_json = result_data
            session.commit()


@router.get("/history")
async def get_history(agent_id: Optional[int] = Query(default=None)):
    """List past backtest runs, newest first."""
    with get_db_session(settings.DATABASE_URL) as session:
        q = select(BacktestResult).order_by(BacktestResult.run_at.desc()).limit(50)
        if agent_id is not None:
            q = q.where(BacktestResult.agent_id == agent_id)
        results = session.execute(q).scalars().all()

    return [
        {
            "id": r.id,
            "agent_id": r.agent_id,
            "run_at": r.run_at.isoformat(),
            "start_date": r.start_date,
            "end_date": r.end_date,
            "mode": r.mode,
            "status": r.status,
        }
        for r in results
    ]


@router.get("/{run_id}")
async def get_run(run_id: str):
    """Poll a single backtest run — returns status + result_json when done."""
    with get_db_session(settings.DATABASE_URL) as session:
        row = session.execute(
            select(BacktestResult).where(BacktestResult.id == run_id)
        ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail=f"Backtest run {run_id} not found")

    return {
        "id": row.id,
        "agent_id": row.agent_id,
        "status": row.status,
        "mode": row.mode,
        "start_date": row.start_date,
        "end_date": row.end_date,
        "run_at": row.run_at.isoformat(),
        "result_json": row.result_json,
    }
```

- [ ] **Step 4: Register router in `backend/main.py`**

Add import:
```python
from backend.api.backtest_ui import router as backtest_ui_router
```

Add registration after `analytics_router`:
```python
app.include_router(backtest_ui_router)
```

- [ ] **Step 5: Run tests**

```bash
pytest tests/test_backtest_ui.py -v
```

Expected: all 5 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/api/backtest_ui.py tests/test_backtest_ui.py backend/main.py
git commit -m "feat: add backtest UI API with run/poll/history endpoints"
```

---

## Task 6: Wire Snapshot Job into Scheduler

**Files:**
- Modify: `backend/main.py`

**Interfaces:**
- Consumes: `run_eod_snapshot` from `backend.analytics.snapshot_job`; APScheduler already in use via `backend.orchestrator.agent_orchestrator`

- [ ] **Step 1: Check APScheduler import in orchestrator**

```bash
grep -n "AsyncIOScheduler\|apscheduler" backend/orchestrator/agent_orchestrator.py | head -5
```

Note the import style used.

- [ ] **Step 2: Add snapshot job to lifespan in `backend/main.py`**

In the `lifespan` function in `backend/main.py`, after `await _orchestrator.initialize()`, add:

```python
        # Schedule EOD snapshot job (fires at 16:05 EST = 21:05 UTC)
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            from backend.analytics.snapshot_job import run_eod_snapshot

            _snapshot_scheduler = AsyncIOScheduler()
            _snapshot_scheduler.add_job(
                run_eod_snapshot,
                trigger="cron",
                hour=21,
                minute=5,
                args=[settings.DATABASE_URL],
                id="eod_snapshot",
                replace_existing=True,
            )
            _snapshot_scheduler.start()
            logger.info("EOD snapshot scheduler started (21:05 UTC daily)")
        except Exception as e:
            logger.warning(f"Snapshot scheduler startup skipped: {e}")
```

Also add before the `yield` shutdown section:

```python
    _snapshot_scheduler = None  # declare at top of lifespan
```

And in the shutdown block after `yield`:

```python
    if _snapshot_scheduler and _snapshot_scheduler.running:
        _snapshot_scheduler.shutdown(wait=False)
```

- [ ] **Step 3: Verify app still starts**

```bash
python -m backend.main &
sleep 3
curl -s http://localhost:8000/api/health | python3 -m json.tool
kill %1
```

Expected: `"status": "ok"` in JSON response.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py
git commit -m "feat: schedule EOD snapshot job at 21:05 UTC via APScheduler"
```

---

## Task 7: Frontend API Client + Store

**Files:**
- Modify: `frontend/src/utils/api-client.js`
- Create: `frontend/src/stores/analytics.store.js`

**Interfaces:**
- Produces:
  - `analyticsApi.portfolio()` → GET `/api/analytics/portfolio`
  - `analyticsApi.equityCurve(days, agentId)` → GET `/api/analytics/equity-curve?days=X&agent_id=Y`
  - `analyticsApi.leaderboard(sortBy)` → GET `/api/analytics/leaderboard?sort_by=X`
  - `analyticsApi.correlation()` → GET `/api/analytics/correlation`
  - `analyticsApi.attribution(dateStr)` → GET `/api/analytics/attribution?date=X`
  - `backtestApi.run(payload)` → POST `/api/backtest/run`
  - `backtestApi.poll(runId)` → GET `/api/backtest/{runId}`
  - `backtestApi.history(agentId)` → GET `/api/backtest/history?agent_id=X`

- [ ] **Step 1: Add API methods to `frontend/src/utils/api-client.js`**

At the end of `frontend/src/utils/api-client.js`, append:

```js
export const analyticsApi = {
  portfolio: () => apiClient.get('/api/analytics/portfolio'),
  equityCurve: (days = 30, agentId = null) => {
    const params = new URLSearchParams({ days });
    if (agentId != null) params.append('agent_id', agentId);
    return apiClient.get(`/api/analytics/equity-curve?${params}`);
  },
  leaderboard: (sortBy = 'return') =>
    apiClient.get(`/api/analytics/leaderboard?sort_by=${sortBy}`),
  correlation: () => apiClient.get('/api/analytics/correlation'),
  attribution: (dateStr = null) => {
    const url = dateStr
      ? `/api/analytics/attribution?date=${dateStr}`
      : '/api/analytics/attribution';
    return apiClient.get(url);
  },
};

export const backtestApi = {
  run: (payload) => apiClient.post('/api/backtest/run', payload),
  poll: (runId) => apiClient.get(`/api/backtest/${runId}`),
  history: (agentId = null) => {
    const url = agentId != null
      ? `/api/backtest/history?agent_id=${agentId}`
      : '/api/backtest/history';
    return apiClient.get(url);
  },
};
```

- [ ] **Step 2: Create `frontend/src/stores/analytics.store.js`**

```js
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { analyticsApi, backtestApi } from '../utils/api-client';

const useAnalyticsStore = create(
  devtools(
    (set, get) => ({
      portfolio: null,
      equityCurve: [],
      leaderboard: [],
      leaderboardSort: 'return',
      correlation: {},
      attribution: null,
      backtestRunId: null,
      backtestStatus: null,   // 'running' | 'done' | 'failed' | null
      backtestResult: null,
      backtestHistory: [],
      loading: false,
      error: null,

      fetchPortfolio: async () => {
        try {
          const data = await analyticsApi.portfolio();
          set({ portfolio: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchEquityCurve: async (days = 30, agentId = null) => {
        set({ loading: true });
        try {
          const data = await analyticsApi.equityCurve(days, agentId);
          set({ equityCurve: data, loading: false });
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      fetchLeaderboard: async (sortBy = 'return') => {
        set({ leaderboardSort: sortBy });
        try {
          const data = await analyticsApi.leaderboard(sortBy);
          set({ leaderboard: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchCorrelation: async () => {
        try {
          const data = await analyticsApi.correlation();
          set({ correlation: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      fetchAttribution: async (dateStr = null) => {
        try {
          const data = await analyticsApi.attribution(dateStr);
          set({ attribution: data });
        } catch (err) {
          set({ error: err.message });
        }
      },

      runBacktest: async (payload) => {
        set({ backtestRunId: null, backtestStatus: 'running', backtestResult: null });
        try {
          const { run_id } = await backtestApi.run(payload);
          set({ backtestRunId: run_id });
          get()._pollBacktest(run_id);
        } catch (err) {
          set({ backtestStatus: 'failed', error: err.message });
        }
      },

      _pollBacktest: async (runId) => {
        const poll = async () => {
          try {
            const data = await backtestApi.poll(runId);
            if (data.status === 'running') {
              setTimeout(poll, 2000);
            } else {
              set({ backtestStatus: data.status, backtestResult: data.result_json });
            }
          } catch (err) {
            set({ backtestStatus: 'failed', error: err.message });
          }
        };
        poll();
      },

      fetchBacktestHistory: async (agentId = null) => {
        try {
          const data = await backtestApi.history(agentId);
          set({ backtestHistory: data });
        } catch (err) {
          set({ error: err.message });
        }
      },
    }),
    { name: 'analytics-store' }
  )
);

export default useAnalyticsStore;
```

- [ ] **Step 3: Verify no import errors**

```bash
cd frontend && node -e "console.log('ok')" && cd ..
```

(Full lint/build verified in Task 12.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/api-client.js frontend/src/stores/analytics.store.js
git commit -m "feat: add analyticsApi/backtestApi client methods and analytics Zustand store"
```

---

## Task 8: EquityChart Component

**Files:**
- Create: `frontend/src/components/Analytics/EquityChart.jsx`

**Interfaces:**
- Props: `data: Array<{date: string, pnl: number}>`, `height?: number`
- Consumes: Recharts `LineChart`, `Line`, `XAxis`, `YAxis`, `Tooltip`, `ResponsiveContainer`, `CartesianGrid`

- [ ] **Step 1: Create component**

```bash
mkdir -p frontend/src/components/Analytics
```

Create `frontend/src/components/Analytics/EquityChart.jsx`:

```jsx
import React from 'react';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';

const fmt = (val) =>
  val >= 0 ? `+$${val.toFixed(0)}` : `-$${Math.abs(val).toFixed(0)}`;

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  const val = payload[0].value;
  return (
    <div style={{
      background: 'var(--color-bg-elevated)',
      border: '1px solid var(--color-border-bright)',
      padding: '8px 12px',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-xs)',
    }}>
      <div style={{ color: 'var(--color-text-secondary)', marginBottom: 4 }}>{label}</div>
      <div style={{ color: val >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)', fontWeight: 700 }}>
        {fmt(val)}
      </div>
    </div>
  );
};

export default function EquityChart({ data = [], height = 200 }) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 8 }}>
        <CartesianGrid
          strokeDasharray="2 4"
          stroke="var(--color-border-subtle)"
          vertical={false}
        />
        <XAxis
          dataKey="date"
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={{ stroke: 'var(--color-border)' }}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={fmt}
          tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
          tickLine={false}
          axisLine={false}
          width={64}
        />
        <Tooltip content={<CustomTooltip />} />
        <ReferenceLine y={0} stroke="var(--color-border-bright)" strokeDasharray="4 4" />
        <Line
          type="monotone"
          dataKey="pnl"
          stroke="var(--color-accent-secondary)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, fill: 'var(--color-accent-secondary)', stroke: 'var(--color-bg-primary)' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

- [ ] **Step 2: Quick smoke test in browser**

Start dev server and navigate to any page — just confirm no import errors:

```bash
cd frontend && npm start &
sleep 8
curl -s http://localhost:3000 | grep -q "LABOURIOUS\|root" && echo "OK" || echo "FAIL"
kill %1
cd ..
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Analytics/EquityChart.jsx
git commit -m "feat: add EquityChart Recharts component"
```

---

## Task 9: AgentLeaderboard Component

**Files:**
- Create: `frontend/src/components/Analytics/AgentLeaderboard.jsx`

**Interfaces:**
- Props: `rows: Array<{id, name, room, total_pnl, win_rate, sharpe_ratio, total_trades, confidence_score, status}>`, `sortBy: string`, `onSort: (col: string) => void`

- [ ] **Step 1: Create component**

Create `frontend/src/components/Analytics/AgentLeaderboard.jsx`:

```jsx
import React from 'react';

const COL_LABELS = {
  return: 'P&L',
  sharpe: 'Sharpe',
  win_rate: 'Win %',
  trades: 'Trades',
};

const BAR_MAX_WIDTH = 80; // px

function InlineBar({ value, max, color }) {
  const width = max > 0 ? Math.max(2, (Math.abs(value) / max) * BAR_MAX_WIDTH) : 2;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div style={{
        width: BAR_MAX_WIDTH,
        height: 6,
        background: 'var(--color-bg-elevated)',
        borderRadius: 3,
        overflow: 'hidden',
      }}>
        <div style={{ width, height: '100%', background: color, borderRadius: 3 }} />
      </div>
    </div>
  );
}

export default function AgentLeaderboard({ rows = [], sortBy = 'return', onSort }) {
  const maxPnl = Math.max(...rows.map((r) => Math.abs(r.total_pnl)), 1);

  const col = (key, label) => (
    <th
      onClick={() => onSort?.(key)}
      style={{
        padding: '6px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--font-size-xs)',
        color: sortBy === key ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
        letterSpacing: '0.08em',
        cursor: 'pointer',
        userSelect: 'none',
        textAlign: 'left',
        borderBottom: '1px solid var(--color-border)',
        whiteSpace: 'nowrap',
      }}
    >
      {label} {sortBy === key ? '▼' : ''}
    </th>
  );

  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          {col('return', 'AGENT')}
          {col('return', 'P&L')}
          <th style={{ padding: '6px 12px', borderBottom: '1px solid var(--color-border)' }} />
          {col('win_rate', 'WIN %')}
          {col('sharpe', 'SHARPE')}
          {col('trades', 'TRADES')}
          <th style={{ padding: '6px 12px', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', letterSpacing: '0.08em', borderBottom: '1px solid var(--color-border)', fontFamily: 'var(--font-mono)' }}>CONF</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => {
          const pnlColor = row.total_pnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';
          return (
            <tr
              key={row.id}
              style={{
                background: i % 2 === 0 ? 'transparent' : 'var(--color-bg-card)',
                transition: 'background var(--transition-fast)',
              }}
            >
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-primary)' }}>
                {row.name}
                <span style={{ marginLeft: 6, fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
                  {row.room?.replace('_', ' ')}
                </span>
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: pnlColor, fontWeight: 700, whiteSpace: 'nowrap' }}>
                {row.total_pnl >= 0 ? '+' : ''}{row.total_pnl.toFixed(2)}
              </td>
              <td style={{ padding: '7px 12px' }}>
                <InlineBar value={row.total_pnl} max={maxPnl} color={pnlColor} />
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {row.win_rate.toFixed(1)}%
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: row.sharpe_ratio != null ? 'var(--color-accent-secondary)' : 'var(--color-text-muted)' }}>
                {row.sharpe_ratio != null ? row.sharpe_ratio.toFixed(2) : '—'}
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-secondary)' }}>
                {row.total_trades}
              </td>
              <td style={{ padding: '7px 12px', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)', color: 'var(--color-text-muted)' }}>
                {row.confidence_score}%
              </td>
            </tr>
          );
        })}
        {rows.length === 0 && (
          <tr>
            <td colSpan={7} style={{ padding: '24px 12px', textAlign: 'center', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
              No agents yet
            </td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Analytics/AgentLeaderboard.jsx
git commit -m "feat: add sortable AgentLeaderboard component with inline bars"
```

---

## Task 10: CorrelationMatrix Component

**Files:**
- Create: `frontend/src/components/Analytics/CorrelationMatrix.jsx`

**Interfaces:**
- Props: `data: Record<string, Record<string, number>>` — e.g. `{"News": {"Energy": 0.18, ...}, ...}`

- [ ] **Step 1: Create component**

Create `frontend/src/components/Analytics/CorrelationMatrix.jsx`:

```jsx
import React from 'react';

const HIGH_CORR_THRESHOLD = 0.7;

export default function CorrelationMatrix({ data = {} }) {
  const agents = Object.keys(data);
  // Collect all unique agent names (including those only appearing as values)
  const allNames = new Set(agents);
  agents.forEach((a) => Object.keys(data[a] || {}).forEach((b) => allNames.add(b)));
  const names = Array.from(allNames).sort();

  if (names.length === 0) {
    return (
      <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
        Insufficient data — need 30+ days of snapshots
      </p>
    );
  }

  const cell = (a, b) => {
    if (a === b) return { value: null, high: false };
    const v = data[a]?.[b] ?? data[b]?.[a] ?? null;
    return { value: v, high: v != null && Math.abs(v) >= HIGH_CORR_THRESHOLD };
  };

  const tdBase = {
    padding: '6px 14px',
    fontFamily: 'var(--font-mono)',
    fontSize: 'var(--font-size-xs)',
    borderBottom: '1px solid var(--color-border-subtle)',
    textAlign: 'center',
    whiteSpace: 'nowrap',
  };

  return (
    <div style={{ overflowX: 'auto' }}>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 8 }}>
        LAST 30D DAILY RETURNS &nbsp;
        <span style={{ color: 'var(--color-accent-warning)' }}>⚠ = corr &gt; 0.7</span>
      </p>
      <table style={{ borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={{ ...tdBase, color: 'var(--color-text-muted)', textAlign: 'left' }} />
            {names.map((n) => (
              <th key={n} style={{ ...tdBase, color: 'var(--color-accent-secondary)' }}>{n}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {names.map((a, i) => (
            <tr key={a} style={{ background: i % 2 === 0 ? 'transparent' : 'var(--color-bg-card)' }}>
              <td style={{ ...tdBase, color: 'var(--color-accent-secondary)', textAlign: 'left', paddingLeft: 0 }}>{a}</td>
              {names.map((b) => {
                const { value, high } = cell(a, b);
                if (value === null) {
                  return (
                    <td key={b} style={{ ...tdBase, color: 'var(--color-text-muted)' }}>—</td>
                  );
                }
                return (
                  <td
                    key={b}
                    style={{
                      ...tdBase,
                      color: high ? 'var(--color-accent-warning)' : 'var(--color-text-primary)',
                    }}
                  >
                    {high && '⚠ '}{value.toFixed(2)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Analytics/CorrelationMatrix.jsx
git commit -m "feat: add CorrelationMatrix component with amber warning flags"
```

---

## Task 11: AttributionWaterfall + BacktestRunner Components

**Files:**
- Create: `frontend/src/components/Analytics/AttributionWaterfall.jsx`
- Create: `frontend/src/components/Analytics/BacktestRunner.jsx`

**Interfaces:**
- `AttributionWaterfall` props: `data: {date: string, contributions: Record<string, number>}`
- `BacktestRunner` props: `agents: Array<{id: number, name: string}>` (for dropdown)

- [ ] **Step 1: Create AttributionWaterfall**

Create `frontend/src/components/Analytics/AttributionWaterfall.jsx`:

```jsx
import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Cell,
  ReferenceLine,
} from 'recharts';

export default function AttributionWaterfall({ data = null }) {
  if (!data || !data.contributions || Object.keys(data.contributions).length === 0) {
    return (
      <p style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
        No trades closed on this date
      </p>
    );
  }

  const entries = Object.entries(data.contributions)
    .sort((a, b) => b[1] - a[1]);

  const chartData = entries.map(([name, pct]) => ({ name, pct }));

  const CustomTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null;
    const val = payload[0].value;
    return (
      <div style={{
        background: 'var(--color-bg-elevated)',
        border: '1px solid var(--color-border-bright)',
        padding: '8px 12px',
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--font-size-xs)',
      }}>
        <div style={{ color: 'var(--color-text-secondary)', marginBottom: 2 }}>{label}</div>
        <div style={{ color: val >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)', fontWeight: 700 }}>
          {val >= 0 ? '+' : ''}{val.toFixed(1)}%
        </div>
      </div>
    );
  };

  return (
    <div>
      <p style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 8 }}>
        P&L ATTRIBUTION — {data.date}
      </p>
      <ResponsiveContainer width="100%" height={180}>
        <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 24, left: 8 }}>
          <XAxis
            dataKey="name"
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={{ stroke: 'var(--color-border)' }}
          />
          <YAxis
            tickFormatter={(v) => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`}
            tick={{ fontFamily: 'var(--font-mono)', fontSize: 9, fill: 'var(--color-text-muted)' }}
            tickLine={false}
            axisLine={false}
            width={48}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={0} stroke="var(--color-border-bright)" />
          <Bar dataKey="pct" radius={[2, 2, 0, 0]}>
            {chartData.map((entry) => (
              <Cell
                key={entry.name}
                fill={entry.pct >= 0 ? 'var(--color-accent-primary)' : 'var(--color-accent-danger)'}
                opacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: Create BacktestRunner**

Create `frontend/src/components/Analytics/BacktestRunner.jsx`:

```jsx
import React, { useState } from 'react';
import useAnalyticsStore from '../../stores/analytics.store';
import EquityChart from './EquityChart';

const inputStyle = {
  background: 'var(--color-bg-tertiary)',
  border: '1px solid var(--color-border)',
  color: 'var(--color-text-primary)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-sm)',
  padding: '6px 10px',
  borderRadius: 'var(--radius-sm)',
};

const labelStyle = {
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-xs)',
  color: 'var(--color-text-muted)',
  letterSpacing: '0.08em',
  marginBottom: 4,
  display: 'block',
};

export default function BacktestRunner({ agents = [] }) {
  const { runBacktest, backtestStatus, backtestResult, backtestHistory } = useAnalyticsStore();
  const [form, setForm] = useState({
    agent_id: agents[0]?.id ?? '',
    start_date: '2024-01-01',
    end_date: '2024-06-30',
    mode: 'basic',
  });

  const handleRun = () => {
    if (!form.agent_id) return;
    runBacktest({ ...form, agent_id: Number(form.agent_id) });
  };

  const equityData = backtestResult?.equity_curve ?? [];
  const stats = backtestResult ?? {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
      {/* Form */}
      <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <span style={labelStyle}>AGENT</span>
          <select
            style={{ ...inputStyle, cursor: 'pointer' }}
            value={form.agent_id}
            onChange={(e) => setForm({ ...form, agent_id: e.target.value })}
          >
            {agents.length === 0 && <option value="">No agents</option>}
            {agents.map((a) => (
              <option key={a.id} value={a.id}>{a.name}</option>
            ))}
          </select>
        </div>
        <div>
          <span style={labelStyle}>FROM</span>
          <input style={inputStyle} type="date" value={form.start_date}
            onChange={(e) => setForm({ ...form, start_date: e.target.value })} />
        </div>
        <div>
          <span style={labelStyle}>TO</span>
          <input style={inputStyle} type="date" value={form.end_date}
            onChange={(e) => setForm({ ...form, end_date: e.target.value })} />
        </div>
        <div>
          <span style={labelStyle}>MODE</span>
          <div style={{ display: 'flex', gap: 'var(--space-3)', alignItems: 'center' }}>
            {['basic', 'walk_forward'].map((m) => (
              <label key={m} style={{ ...labelStyle, marginBottom: 0, cursor: 'pointer', color: form.mode === m ? 'var(--color-text-primary)' : undefined }}>
                <input type="radio" name="mode" value={m} checked={form.mode === m}
                  onChange={() => setForm({ ...form, mode: m })}
                  style={{ marginRight: 4 }} />
                {m === 'basic' ? 'Basic' : 'Walk-Fwd'}
              </label>
            ))}
          </div>
        </div>
        <button
          onClick={handleRun}
          disabled={backtestStatus === 'running' || !form.agent_id}
          style={{
            ...inputStyle,
            background: 'var(--color-bg-elevated)',
            border: '1px solid var(--color-accent-primary)',
            color: 'var(--color-accent-primary)',
            cursor: backtestStatus === 'running' ? 'not-allowed' : 'pointer',
            letterSpacing: '0.08em',
            opacity: backtestStatus === 'running' ? 0.6 : 1,
          }}
        >
          {backtestStatus === 'running' ? '⟳ RUNNING...' : '▶ RUN BACKTEST'}
        </button>
      </div>

      {/* Results */}
      {backtestStatus === 'done' && stats && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', borderTop: '1px solid var(--color-border)', paddingTop: 'var(--space-4)' }}>
          <div style={{ display: 'flex', gap: 'var(--space-6)', flexWrap: 'wrap' }}>
            {[
              { label: 'RETURN', value: stats.total_return != null ? `${stats.total_return > 0 ? '+' : ''}${stats.total_return.toFixed(1)}%` : '—', color: (stats.total_return ?? 0) >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)' },
              { label: 'WIN RATE', value: stats.win_rate != null ? `${stats.win_rate.toFixed(1)}%` : '—', color: 'var(--color-text-primary)' },
              { label: 'SHARPE', value: stats.sharpe_ratio != null ? stats.sharpe_ratio.toFixed(2) : '—', color: 'var(--color-accent-secondary)' },
              { label: 'MAX DD', value: stats.max_drawdown != null ? `${(stats.max_drawdown * 100).toFixed(1)}%` : '—', color: 'var(--color-accent-warning)' },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <span style={{ ...labelStyle }}>{label}</span>
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-lg)', fontWeight: 700, color }}>{value}</span>
              </div>
            ))}
          </div>
          {equityData.length > 0 && <EquityChart data={equityData} height={160} />}
        </div>
      )}

      {backtestStatus === 'failed' && (
        <p style={{ color: 'var(--color-accent-danger)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-sm)' }}>
          Backtest failed: {backtestResult?.error ?? 'unknown error'}
        </p>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Analytics/AttributionWaterfall.jsx frontend/src/components/Analytics/BacktestRunner.jsx
git commit -m "feat: add AttributionWaterfall and BacktestRunner components"
```

---

## Task 12: AnalyticsPage + Route + Nav Item

**Files:**
- Create: `frontend/src/pages/AnalyticsPage.jsx`
- Modify: `frontend/src/App.jsx`

**Interfaces:**
- Consumes: all Analytics components; `useAnalyticsStore`; `useAgentsStore` for agent list in BacktestRunner

- [ ] **Step 1: Create `frontend/src/pages/AnalyticsPage.jsx`**

```jsx
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import useAnalyticsStore from '../stores/analytics.store';
import useAgentsStore from '../stores/agents.store';
import EquityChart from '../components/Analytics/EquityChart';
import AgentLeaderboard from '../components/Analytics/AgentLeaderboard';
import CorrelationMatrix from '../components/Analytics/CorrelationMatrix';
import AttributionWaterfall from '../components/Analytics/AttributionWaterfall';
import BacktestRunner from '../components/Analytics/BacktestRunner';

const sectionStyle = {
  background: 'var(--color-bg-card)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-md)',
  padding: 'var(--space-6)',
  marginBottom: 'var(--space-6)',
};

const sectionHeader = {
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--font-size-xs)',
  letterSpacing: '0.12em',
  color: 'var(--color-text-muted)',
  marginBottom: 'var(--space-4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
};

const kpiBox = (label, value, color) => (
  <div key={label} style={{
    background: 'var(--color-bg-elevated)',
    border: '1px solid var(--color-border)',
    borderRadius: 'var(--radius-sm)',
    padding: 'var(--space-4) var(--space-6)',
    minWidth: 120,
  }}>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', marginBottom: 4, letterSpacing: '0.08em' }}>{label}</div>
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xl)', fontWeight: 700, color: color ?? 'var(--color-text-primary)' }}>{value}</div>
  </div>
);

const TIME_RANGES = [
  { label: '7D', days: 7 },
  { label: '30D', days: 30 },
  { label: '90D', days: 90 },
  { label: 'ALL', days: 365 },
];

export default function AnalyticsPage() {
  const {
    portfolio, equityCurve, leaderboard, leaderboardSort,
    correlation, attribution,
    fetchPortfolio, fetchEquityCurve, fetchLeaderboard,
    fetchCorrelation, fetchAttribution,
  } = useAnalyticsStore();
  const { agents, fetchAgents } = useAgentsStore();

  const [activeDays, setActiveDays] = useState(30);

  useEffect(() => {
    fetchPortfolio();
    fetchEquityCurve(activeDays);
    fetchLeaderboard(leaderboardSort);
    fetchCorrelation();
    fetchAttribution();
    fetchAgents();
  }, []);

  const handleDaysChange = (days) => {
    setActiveDays(days);
    fetchEquityCurve(days);
  };

  const p = portfolio;
  const totalPnlColor = p?.total_pnl >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)';

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.18, ease: 'easeOut' }}
    >
      {/* Portfolio Performance */}
      <div style={sectionStyle}>
        <div style={sectionHeader}>
          <span>PORTFOLIO PERFORMANCE</span>
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            {TIME_RANGES.map(({ label, days }) => (
              <button
                key={label}
                onClick={() => handleDaysChange(days)}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 'var(--font-size-xs)',
                  padding: '2px 8px',
                  background: activeDays === days ? 'var(--color-bg-elevated)' : 'transparent',
                  border: `1px solid ${activeDays === days ? 'var(--color-accent-primary)' : 'var(--color-border)'}`,
                  color: activeDays === days ? 'var(--color-accent-primary)' : 'var(--color-text-muted)',
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                }}
              >{label}</button>
            ))}
          </div>
        </div>

        <EquityChart data={equityCurve} height={200} />

        <div style={{ display: 'flex', gap: 'var(--space-4)', flexWrap: 'wrap', marginTop: 'var(--space-6)' }}>
          {kpiBox('TOTAL P&L', p ? `${p.total_pnl >= 0 ? '+' : ''}$${p.total_pnl?.toFixed(2) ?? '—'}` : '—', totalPnlColor)}
          {kpiBox('SHARPE', p?.sharpe_ratio != null ? p.sharpe_ratio.toFixed(2) : '—', 'var(--color-accent-secondary)')}
          {kpiBox('MAX DD', p?.max_drawdown != null ? `${(p.max_drawdown * 100).toFixed(1)}%` : '—', 'var(--color-accent-warning)')}
          {kpiBox('WIN RATE', p?.win_rate != null ? `${p.win_rate.toFixed(1)}%` : '—', 'var(--color-text-primary)')}
          {kpiBox('30D RETURN', p?.return_30d_pct != null ? `${p.return_30d_pct >= 0 ? '+' : ''}${p.return_30d_pct.toFixed(2)}%` : '—', p?.return_30d_pct >= 0 ? 'var(--color-pnl-positive)' : 'var(--color-pnl-negative)')}
        </div>
      </div>

      {/* Agent Leaderboard */}
      <div style={sectionStyle}>
        <div style={sectionHeader}>
          <span>AGENT LEADERBOARD</span>
        </div>
        <AgentLeaderboard
          rows={leaderboard}
          sortBy={leaderboardSort}
          onSort={(col) => fetchLeaderboard(col)}
        />
      </div>

      {/* Correlation Matrix */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>CORRELATION MATRIX</span></div>
        <CorrelationMatrix data={correlation} />
      </div>

      {/* Attribution */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>P&L ATTRIBUTION</span></div>
        <AttributionWaterfall data={attribution} />
      </div>

      {/* Backtest Runner */}
      <div style={sectionStyle}>
        <div style={sectionHeader}><span>BACKTEST</span></div>
        <BacktestRunner agents={agents} />
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Add route + nav item to `frontend/src/App.jsx`**

Add import at top with other page imports:
```js
import AnalyticsPage from './pages/AnalyticsPage';
```

In `NAV_ITEMS` array, add after the `Long-Term` entry:
```js
{ label: 'Analytics', path: '/analytics', icon: '◈' },
```

In `<Routes>` block, add after the long-term warroom route:
```jsx
<Route path="/analytics" element={
  <motion.div variants={pageVariants} initial="initial" animate="animate" exit="exit" transition={pageTransition}>
    <AnalyticsPage />
  </motion.div>
} />
```

- [ ] **Step 3: Start dev server and verify**

```bash
cd frontend && npm start &
sleep 10
curl -s http://localhost:3000 | grep -q "LABOURIOUS\|root" && echo "OK"
kill %1
cd ..
```

Navigate to `http://localhost:3000/analytics` manually — confirm:
- Page loads without error
- All 5 sections render (may be empty/loading if no data)
- Sidebar shows Analytics nav item

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.jsx frontend/src/App.jsx
git commit -m "feat: add AnalyticsPage with all sections wired, register /analytics route and nav item"
```

---

## Self-Review

**Spec coverage check:**
- ✅ `daily_snapshots` table — Task 1
- ✅ `backtest_results` table — Task 1
- ✅ `compute_sharpe`, `compute_max_drawdown`, `compute_correlation_matrix`, `compute_attribution` — Task 2
- ✅ EOD snapshot job at 16:05 EST — Task 3 + Task 6
- ✅ `/api/analytics/portfolio` — Task 4
- ✅ `/api/analytics/equity-curve` — Task 4
- ✅ `/api/analytics/leaderboard` — Task 4
- ✅ `/api/analytics/correlation` — Task 4
- ✅ `/api/analytics/attribution` — Task 4
- ✅ `POST /api/backtest/run` — Task 5
- ✅ `GET /api/backtest/{run_id}` — Task 5
- ✅ `GET /api/backtest/history` — Task 5
- ✅ `EquityChart.jsx` — Task 8
- ✅ `AgentLeaderboard.jsx` (sortable) — Task 9
- ✅ `CorrelationMatrix.jsx` (numbers + amber flags) — Task 10
- ✅ `AttributionWaterfall.jsx` — Task 11
- ✅ `BacktestRunner.jsx` (inline, form + results) — Task 11
- ✅ `AnalyticsPage.jsx` (single-scroll, time range selector) — Task 12
- ✅ `/analytics` route + sidebar nav item — Task 12
- ✅ Color palette: CSS vars only, no hacker-green — all tasks
- ✅ JetBrains Mono: unchanged, all tasks reference `--font-mono`
- ✅ Security: no API keys in logs, read-only analytics endpoints

**Placeholder scan:** No TBD, TODO, or vague steps found.

**Type consistency:**
- `run_eod_snapshot(database_url: str)` — defined Task 3, called Task 6 ✅
- `analyticsApi` — defined Task 7, consumed Task 12 via store ✅
- `backtestApi` — defined Task 7, consumed Task 7 store ✅
- `useAnalyticsStore` — defined Task 7, imported Task 11 (BacktestRunner) and Task 12 ✅
- `EquityChart` props `data: Array<{date, pnl}>` — produced by `/equity-curve` endpoint Task 4, consumed Task 8 + Task 11 ✅
- `AgentLeaderboard` props `rows`, `sortBy`, `onSort` — all passed from Task 12 ✅
- `AttributionWaterfall` props `data: {date, contributions}` — shape matches `attribution` endpoint Task 4 ✅
