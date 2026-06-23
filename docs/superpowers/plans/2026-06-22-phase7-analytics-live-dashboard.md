# Phase 7 — Analytics & Live Dashboard

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire all existing analytics components to real data. Every KPI on Dashboard, Lobby, and AnalyticsPage is currently either hardcoded, using stale endpoints, or missing live refresh. Phase 7 makes the trading warroom show real numbers — live-updating via WebSocket events and polling.

**What exists (use it, don't re-create):**
- `backend/api/analytics.py` — `/api/analytics/portfolio`, `/equity-curve`, `/leaderboard`, `/correlation`, `/attribution` — all working
- `backend/api/dashboard.py` — `/api/dashboard/summary`, `/equity-curve`, `/performance`, `/allocation`, `/risk`
- `frontend/src/stores/analytics.store.js` — `fetchPortfolio`, `fetchEquityCurve`, `fetchLeaderboard`, `fetchCorrelation`, `fetchAttribution`
- `frontend/src/stores/dashboard.store.js` — `fetchPortfolioSummary`, `fetchPortfolioHistory`, `fetchSystemHealth`
- `frontend/src/components/Analytics/` — `EquityChart`, `AgentLeaderboard`, `CorrelationMatrix`, `AttributionWaterfall` — components exist, receive data via props/store
- `DailySnapshot` model + writes after each trade (Phase 6A.6 done)

**Root problem:** The UI renders real components but data is stale (fetched once on mount, no refresh). WebSocket events (trade_executed, agent_update) never trigger a re-fetch. Dashboard equity curve uses `Performance` table; Analytics uses `DailySnapshot` — inconsistency causes different charts to show different numbers.

**Architecture:**
```
Phase 7 scope:
  7A — Fix Dashboard data: wire dashboardApi to correct endpoints, add 30s auto-refresh
  7B — Live refresh: WS trade_executed events trigger targeted store updates (no full reload)
  7C — Analytics page completeness: CorrelationMatrix + AttributionWaterfall empty-state + date picker
  7D — Lobby live stats: pull from analytics/portfolio not performanceApi; WS-reactive
  7E — /api/health/full: broker ping + LLM ping + vault status; wire to SystemHealthPanel
```

**Constraints (same as prior phases):**
- No new npm packages. All frontend uses existing: Recharts, Framer Motion, Zustand.
- All colors via `var(--color-*)` only.
- Backend: no new DB models. Use existing analytics endpoints.
- Commit per task: `feat(7X.Y): description` pattern.
- TDD-adjacent: backend tasks get a failing test first.
- Run `pytest tests/ -v --asyncio-mode=auto` before every backend commit.

---

## Global Constraints

- Dashboard equity curve: use `/api/analytics/equity-curve` (not `/api/dashboard/equity-curve` — that pulls from `Performance` table which is written less consistently than `DailySnapshot`). Consolidate on `DailySnapshot` as source of truth.
- Auto-refresh on Dashboard/Analytics: `setInterval` at 30s. Clear on unmount. Do NOT use `useEffect` with rapid intervals — 30s is the floor.
- WebSocket reactive update: `useWebSocketStore` already exposes `lastMessage`. On `trade_executed` or `agent_update` WS events, call the relevant store fetch. No full page refresh.
- `portfolio_value` and `cash_balance` columns missing from `DailySnapshot` model — add via Alembic migration in 7A.

---

## File Map

### Files to Modify

| File | What changes |
|------|-------------|
| `backend/database/models.py` | Add `portfolio_value`, `cash_balance` to `DailySnapshot` (Alembic) |
| `backend/api/analytics.py` | Add `GET /api/analytics/health` endpoint (broker + LLM + vault status) |
| `backend/api/health.py` | Add `GET /api/health/full` delegating to analytics health checks |
| `frontend/src/pages/Dashboard.jsx` | Switch equity curve to `/api/analytics/equity-curve`; add 30s auto-refresh; WS-reactive |
| `frontend/src/pages/Lobby.jsx` | Use `analyticsApi.portfolio()` for stats; subscribe to WS trade events for refresh |
| `frontend/src/pages/AnalyticsPage.jsx` | Add attribution date picker; wire correlation empty-state message |
| `frontend/src/stores/dashboard.store.js` | Add `fetchPortfolioSummary` that uses `analyticsApi`; add `startAutoRefresh`/`stopAutoRefresh` |
| `frontend/src/components/Analytics/CorrelationMatrix.jsx` | Empty-state when <2 agents have data |
| `frontend/src/components/Analytics/AttributionWaterfall.jsx` | Attribution date picker; empty-state |
| `frontend/src/components/SystemHealthPanel.jsx` | Show broker + LLM status from `/api/health/full` |
| `frontend/src/utils/api-client.js` | Add `analyticsApi.healthFull`; `healthApi.full` |

### Files to Create

| File | Purpose |
|------|---------|
| `alembic/versions/xxxx_add_portfolio_value_to_daily_snapshot.py` | Add `portfolio_value`, `cash_balance` to `DailySnapshot` |
| `tests/test_analytics_api.py` | Coverage for new /health endpoint |

---

## WebSocket Events (Phase 7 reactive)

Frontend listens for these from `useWebSocketStore().lastMessage`:

```js
// On receipt, trigger targeted re-fetch:
'trade_executed'  → fetchPortfolio() + fetchEquityCurve(activeDays) + fetchLeaderboard(sort)
'agent_update'    → fetchLeaderboard(sort)  // status/confidence may have changed
'agent_paused'    → fetchLeaderboard(sort) + fetchPortfolio()
'live_order_filled' → fetchPortfolio() + fetchEquityCurve(activeDays)
```

Do NOT refetch on every WS message — filter by event type.

---

## Priority A — Dashboard Data Fix

### Task 7A.1: Add missing DailySnapshot columns via Alembic

**Files:**
- Modify: `backend/database/models.py`
- Create: Alembic migration

**Why:** `_upsert_daily_snapshot` in Phase 6A.6 references `portfolio_value` and `cash_balance` but they may be missing from `DailySnapshot` model. This migration ensures schema matches what the trade executor writes.

- [ ] **Step 1: Check if columns already exist**

```bash
cd /Users/coleadams/labourious && source .venv/bin/activate
python -c "from backend.database.models import DailySnapshot; print([c.name for c in DailySnapshot.__table__.columns])"
```

If `portfolio_value` and `cash_balance` are present → skip to 7A.2.

- [ ] **Step 2: Add columns to model if missing**

In `backend/database/models.py`, add to `DailySnapshot`:
```python
    portfolio_value = Column(Float, nullable=True)
    cash_balance = Column(Float, nullable=True)
```

- [ ] **Step 3: Generate and run migration**

```bash
alembic revision --autogenerate -m "add_portfolio_value_cash_balance_to_daily_snapshot"
alembic upgrade head
```

- [ ] **Step 4: Commit**

```bash
git add backend/database/models.py alembic/versions/
git commit -m "feat(7A.1): add portfolio_value/cash_balance to DailySnapshot; Alembic migration"
```

---

### Task 7A.2: Consolidate equity curve source — Dashboard uses analytics endpoint

**Problem:** `Dashboard.jsx` calls `dashboardApi.equityCurve()` → `/api/dashboard/equity-curve` → queries `Performance` table. Analytics page calls `analyticsApi.equityCurve()` → `/api/analytics/equity-curve` → queries `DailySnapshot`. Two charts show different data. `DailySnapshot` is written every trade (Phase 6A.6); `Performance` is not. Use `DailySnapshot` everywhere.

**Files:**
- Modify: `frontend/src/stores/dashboard.store.js`

- [ ] **Step 1: Write failing test**

```python
# tests/test_analytics_api.py — create
import pytest

def test_analytics_equity_curve_returns_list(client, auth_headers):
    """GET /api/analytics/equity-curve returns a list."""
    resp = client.get("/api/analytics/equity-curve?days=30", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)

def test_analytics_portfolio_returns_expected_keys(client, auth_headers):
    """GET /api/analytics/portfolio returns total_pnl and win_rate."""
    resp = client.get("/api/analytics/portfolio", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_pnl" in data
    assert "win_rate" in data
```

- [ ] **Step 2: Run tests**

```bash
pytest tests/test_analytics_api.py -v --asyncio-mode=auto
```

Expected: PASS (endpoints already exist — just coverage)

- [ ] **Step 3: Update `dashboard.store.js` to use analytics endpoint**

Replace `fetchPortfolioHistory` in `dashboard.store.js`:

```javascript
fetchPortfolioHistory: async (days = 30) => {
  try {
    const data = await analyticsApi.equityCurve(days);  // use DailySnapshot source
    set({ portfolioHistory: Array.isArray(data) ? data : [] });
  } catch (err) {
    set({ error: err.message });
  }
},

fetchPortfolioSummary: async () => {
  set({ portfolioLoading: true, error: null });
  try {
    const data = await analyticsApi.portfolio();   // analytics has Sharpe, max DD
    set({
      portfolio: {
        totalValue: data.total_pnl ?? 0,           // best proxy without separate "value" field
        cashBalance: 0,
        unrealizedPnl: 0,
        realizedPnl: data.total_pnl ?? 0,
        totalPnl: data.total_pnl ?? 0,
        totalPnlPct: data.return_30d_pct ?? 0,
        activeAgents: data.agent_count ?? 0,
        totalTrades: 0,
        winRate: data.win_rate ?? 0,
        sharpeRatio: data.sharpe_ratio,
        maxDrawdown: data.max_drawdown,
        return30d: data.return_30d_pct ?? 0,
      },
      portfolioLoading: false,
      lastFetched: Date.now(),
    });
  } catch (err) {
    set({ portfolioLoading: false, error: err.message });
  }
},
```

Add import at top of `dashboard.store.js`:
```javascript
import { analyticsApi, performanceApi, healthApi, dashboardApi, tradesApi } from '../utils/api-client';
```

(analyticsApi is already exported from api-client.js)

- [ ] **Step 4: Update Dashboard.jsx KPI cards to use new portfolio shape**

In `Dashboard.jsx`, KPI cards currently reference `portfolio.totalPnl`, `portfolio.activeAgents`, etc. Add two new KPI cards using the new Sharpe and MaxDD fields from analytics:

```jsx
// In the card grid (add after Win Rate card):
{portfolio.sharpeRatio != null && card('Sharpe', portfolio.sharpeRatio.toFixed(2), 'var(--color-accent-secondary)')}
{portfolio.maxDrawdown != null && card('Max DD', `${(portfolio.maxDrawdown * 100).toFixed(1)}%`, 'var(--color-accent-warning)')}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/dashboard.store.js frontend/src/pages/Dashboard.jsx tests/test_analytics_api.py
git commit -m "feat(7A.2): dashboard equity curve and portfolio stats use analytics/DailySnapshot source; add Sharpe+MaxDD cards"
```

---

### Task 7A.3: Auto-refresh + WebSocket-reactive Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.jsx`
- Modify: `frontend/src/stores/dashboard.store.js`

**Why:** Trades execute in background. Dashboard currently only fetches on mount — user sees stale numbers until page reload.

- [ ] **Step 1: Add `startAutoRefresh`/`stopAutoRefresh` to dashboard.store.js**

Add to the store:
```javascript
_refreshInterval: null,

startAutoRefresh: (intervalMs = 30_000) => {
  const { _refreshInterval } = get();
  if (_refreshInterval) return;  // already running
  const id = setInterval(() => {
    get().fetchPortfolioSummary();
    get().fetchPortfolioHistory();
    get().fetchRecentTrades(20);
  }, intervalMs);
  set({ _refreshInterval: id });
},

stopAutoRefresh: () => {
  const { _refreshInterval } = get();
  if (_refreshInterval) {
    clearInterval(_refreshInterval);
    set({ _refreshInterval: null });
  }
},
```

- [ ] **Step 2: Update Dashboard.jsx to start/stop auto-refresh and react to WS**

In `Dashboard.jsx`, replace the `useEffect` with:

```jsx
const { startAutoRefresh, stopAutoRefresh } = useDashboardStore();
const lastMessage = useWebSocketStore(s => s.lastMessage);

useEffect(() => {
  fetchPortfolioSummary();
  fetchPortfolioHistory();
  fetchAgents();
  fetchRecentTrades(20);
  fetchSystemHealth();
  startAutoRefresh(30_000);
  return () => stopAutoRefresh();
}, []);  // eslint-disable-line

// WS-reactive: re-fetch on trade events
useEffect(() => {
  if (!lastMessage) return;
  const reactive = ['trade_executed', 'live_order_filled', 'agent_update', 'agent_paused'];
  if (reactive.includes(lastMessage.event ?? lastMessage.type)) {
    fetchPortfolioSummary();
    fetchRecentTrades(20);
  }
}, [lastMessage]);
```

Add `useWebSocketStore` import:
```jsx
import { useWebSocketStore } from '../stores/websocket.store';
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/dashboard.store.js frontend/src/pages/Dashboard.jsx
git commit -m "feat(7A.3): 30s auto-refresh on Dashboard; WS-reactive portfolio/trades re-fetch"
```

---

## Priority B — Analytics Page Completeness

### Task 7B.1: CorrelationMatrix empty-state + data check

**Problem:** `CorrelationMatrix` receives `correlation` from store. `compute_correlation_matrix` returns `{}` when <2 agents have DailySnapshot data. Component currently renders nothing — no feedback to user.

**Files:**
- Modify: `frontend/src/components/Analytics/CorrelationMatrix.jsx`

- [ ] **Step 1: Add empty-state render**

Read `CorrelationMatrix.jsx` first (may already have empty state). If not:

```jsx
// In CorrelationMatrix, at top of return:
if (!data || Object.keys(data).length === 0) {
  return (
    <div style={{
      fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)',
      color: 'var(--color-text-muted)', padding: 'var(--space-6)',
      textAlign: 'center', border: '1px dashed var(--color-border)',
      borderRadius: 'var(--radius-sm)',
    }}>
      Correlation requires 2+ agents with 30 days of trade history.
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Analytics/CorrelationMatrix.jsx
git commit -m "feat(7B.1): CorrelationMatrix empty-state when insufficient agent data"
```

---

### Task 7B.2: Attribution date picker + WS refresh

**Problem:** `AttributionWaterfall` shows today's attribution. User cannot browse historical dates. Also no WS refresh trigger.

**Files:**
- Modify: `frontend/src/pages/AnalyticsPage.jsx`
- Modify: `frontend/src/components/Analytics/AttributionWaterfall.jsx`

- [ ] **Step 1: Add attribution date picker to AnalyticsPage.jsx**

In `AnalyticsPage.jsx`, add state and date input in the Attribution section header:

```jsx
const [attributionDate, setAttributionDate] = useState(null);  // null = today

// In the Attribution section header (sectionHeader div):
<div style={sectionHeader}>
  <span>P&L ATTRIBUTION</span>
  <input
    type="date"
    value={attributionDate ?? new Date().toISOString().slice(0, 10)}
    onChange={(e) => {
      setAttributionDate(e.target.value || null);
      fetchAttribution(e.target.value || null);
    }}
    style={{
      background: 'var(--color-bg-elevated)', border: '1px solid var(--color-border)',
      color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-xs)', padding: '2px 6px', borderRadius: 3,
      cursor: 'pointer',
    }}
  />
</div>
```

- [ ] **Step 2: Add WS-reactive attribution refresh to AnalyticsPage**

In `AnalyticsPage.jsx` useEffect, add:

```jsx
const lastMessage = useWebSocketStore(s => s.lastMessage);

useEffect(() => {
  if (!lastMessage) return;
  const reactive = ['trade_executed', 'live_order_filled'];
  if (reactive.includes(lastMessage.event ?? lastMessage.type)) {
    fetchPortfolio();
    fetchEquityCurve(activeDays);
    fetchLeaderboard(leaderboardSort);
    fetchAttribution(attributionDate);
  }
}, [lastMessage]);
```

Import at top:
```jsx
import { useWebSocketStore } from '../stores/websocket.store';
```

- [ ] **Step 3: Add empty-state to AttributionWaterfall**

In `AttributionWaterfall.jsx`, if `data?.contributions` is empty:
```jsx
if (!data?.contributions || Object.keys(data.contributions).length === 0) {
  return (
    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)', padding: 'var(--space-4)', textAlign: 'center' }}>
      No closed trades on {data?.date ?? 'selected date'}.
    </div>
  );
}
```

- [ ] **Step 4: Run full test suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.jsx frontend/src/components/Analytics/AttributionWaterfall.jsx
git commit -m "feat(7B.2): attribution date picker; WS-reactive analytics refresh; AttributionWaterfall empty-state"
```

---

## Priority C — Lobby Live Stats

### Task 7C.1: Lobby uses analytics portfolio; WS-reactive room scorecards

**Problem:** `Lobby.jsx` calls `performanceApi.summary()` which uses legacy `/api/performance/summary`. `RoomScorecard` P&L data comes from agents list only (no per-room analytics). Stats are stale post-mount.

**Files:**
- Modify: `frontend/src/pages/Lobby.jsx`

- [ ] **Step 1: Update Lobby to use analyticsApi.portfolio**

In `Lobby.jsx`, replace `performanceApi.summary().then(setPortfolio)`:

```jsx
import { analyticsApi, agentsApi } from '../utils/api-client';

// In useEffect:
Promise.all([
  agentsApi.list().catch(() => []),
  analyticsApi.portfolio().catch(() => null),
]).then(([agentList, portfolioData]) => {
  setAgents(agentList);
  setPortfolio(portfolioData);
});
```

- [ ] **Step 2: WS-reactive refresh**

Replace the WS-reactive useEffect:

```jsx
useEffect(() => {
  if (!lastMessage) return;
  const reactive = ['trade_executed', 'live_order_filled', 'agent_update', 'agent_paused'];
  if (reactive.includes(lastMessage.event ?? lastMessage.type)) {
    Promise.all([
      agentsApi.list().catch(() => []),
      analyticsApi.portfolio().catch(() => null),
    ]).then(([agentList, portfolioData]) => {
      setAgents(agentList);
      setPortfolio(portfolioData);
    });
  }
}, [lastMessage]);
```

- [ ] **Step 3: Update stat bar to use analytics shape**

The stats bar at the bottom of Lobby uses `portfolio.active_agents`, `portfolio.total_trades`, etc. Update keys to match `analyticsApi.portfolio()` response shape:

```jsx
{ label: 'ACTIVE AGENTS', value: portfolio?.agent_count ?? agents.filter(a => a.status === 'running').length },
{ label: 'TOTAL TRADES', value: portfolio?.total_trades ?? 0 },
{ label: 'WIN RATE', value: `${(portfolio?.win_rate ?? 0).toFixed(1)}%` },
{ label: '30D RETURN', value: portfolio?.return_30d_pct != null ? `${portfolio.return_30d_pct >= 0 ? '+' : ''}${portfolio.return_30d_pct.toFixed(2)}%` : '—' },
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Lobby.jsx
git commit -m "feat(7C.1): Lobby uses analyticsApi.portfolio; WS-reactive room scorecard refresh"
```

---

## Priority D — Full Health Endpoint + SystemHealthPanel

### Task 7D.1: `GET /api/health/full` — broker + LLM + vault status

**Files:**
- Modify: `backend/api/health.py`
- Modify: `frontend/src/components/SystemHealthPanel.jsx`
- Modify: `frontend/src/stores/dashboard.store.js`
- Modify: `frontend/src/utils/api-client.js`

**Why:** `SystemHealthPanel` currently shows only backend + DB status. User cannot see from the Dashboard whether their broker or LLM is actually reachable without going to Control Room.

- [ ] **Step 1: Write failing test**

```python
# tests/test_api_health.py — add

def test_health_full_returns_all_subsystems(client):
    """GET /api/health/full returns backend, db, vault, llm keys."""
    resp = client.get("/api/health/full")
    assert resp.status_code == 200
    data = resp.json()
    assert "backend" in data
    assert "db" in data
    assert "vault" in data
    assert "llm" in data
```

- [ ] **Step 2: Add endpoint to `backend/api/health.py`**

```python
@router.get("/health/full")
async def full_health():
    """Comprehensive health check: backend, DB, vault, LLM."""
    from backend.config import settings
    from backend.database.db import get_db_session
    from sqlalchemy import text

    result = {
        "backend": "ok",
        "uptime_seconds": (datetime.utcnow() - _start_time).total_seconds(),
    }

    # DB
    try:
        with get_db_session(settings.DATABASE_URL) as session:
            session.execute(text("SELECT 1"))
        result["db"] = "ok"
    except Exception as e:
        result["db"] = f"error: {str(e)[:60]}"

    # Vault
    try:
        if settings.VAULT_PASSWORD:
            from backend.vault.encrypted_vault import EncryptedVault
            vault = EncryptedVault(settings.VAULT_PASSWORD)
            _ = vault.list_keys()  # lightweight read
            result["vault"] = "ok"
        else:
            result["vault"] = "no_password"
    except Exception as e:
        result["vault"] = f"error: {str(e)[:60]}"

    # LLM
    try:
        from backend.llm.config import read_config
        cfg = read_config()
        result["llm"] = cfg.get("provider", "unknown") if cfg else "not_configured"
    except Exception:
        result["llm"] = "not_configured"

    return result
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_api_health.py -v --asyncio-mode=auto
```

Expected: PASS

- [ ] **Step 4: Add `healthApi.full` to api-client.js**

```javascript
export const healthApi = {
  check: () => apiClient.get('/api/health'),
  dbCheck: () => apiClient.get('/api/health/db'),
  full: () => apiClient.get('/api/health/full'),
};
```

- [ ] **Step 5: Update dashboard.store.js fetchSystemHealth**

```javascript
fetchSystemHealth: async () => {
  try {
    const data = await healthApi.full();
    set({
      backendStatus: data.backend === 'ok' ? 'connected' : 'degraded',
      backendVersion: data.version ?? null,
      backendUptime: data.uptime_seconds,
      dbStatus: data.db === 'ok' ? 'connected' : 'error',
      vaultStatus: data.vault,
      llmStatus: data.llm,
    });
  } catch {
    set({ backendStatus: 'disconnected', dbStatus: 'error' });
  }
},
```

Add `vaultStatus: 'unknown', llmStatus: 'unknown'` to initial state.

- [ ] **Step 6: Update SystemHealthPanel to show vault + LLM status**

In `frontend/src/components/SystemHealthPanel.jsx`, receive and render `vaultStatus` and `llmStatus` props. Add rows:

```jsx
// Accept additional props: vaultStatus, llmStatus
// Render rows (same style as existing backend/db rows):
{ label: 'VAULT', value: vaultStatus ?? 'unknown' },
{ label: 'LLM', value: llmStatus ?? 'unknown' },
```

Update all call sites that render `<SystemHealthPanel>` to pass the new props from the store.

- [ ] **Step 7: Run full test suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

- [ ] **Step 8: Commit**

```bash
git add backend/api/health.py frontend/src/utils/api-client.js frontend/src/stores/dashboard.store.js frontend/src/components/SystemHealthPanel.jsx
git commit -m "feat(7D.1): /api/health/full — broker+LLM+vault status; SystemHealthPanel shows all subsystems"
```

---

## Priority E — Analytics Page Auto-Refresh

### Task 7E.1: Analytics page 30s auto-refresh

**Files:**
- Modify: `frontend/src/pages/AnalyticsPage.jsx`

**Why:** AnalyticsPage fetches once on mount. During live trading, leaderboard and portfolio numbers go stale quickly.

- [ ] **Step 1: Add auto-refresh interval to AnalyticsPage**

In `AnalyticsPage.jsx`, add to the `useEffect`:

```jsx
// Auto-refresh analytics every 30s
const refreshId = setInterval(() => {
  fetchPortfolio();
  fetchEquityCurve(activeDays);
  fetchLeaderboard(leaderboardSort);
}, 30_000);

return () => clearInterval(refreshId);
```

The existing `useEffect` has `[activeDays, ...]` deps — add the interval inside that effect's return cleanup.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/AnalyticsPage.jsx
git commit -m "feat(7E.1): 30s auto-refresh on AnalyticsPage portfolio + equity curve + leaderboard"
```

---

## Self-Review Checklist

| Requirement | Task |
|-------------|------|
| Dashboard uses DailySnapshot (not Performance) for equity curve | 7A.2 |
| Dashboard Sharpe + MaxDD KPIs visible | 7A.2 |
| Dashboard auto-refresh every 30s | 7A.3 |
| Dashboard WS-reactive on trade_executed | 7A.3 |
| CorrelationMatrix empty-state | 7B.1 |
| Attribution date picker | 7B.2 |
| Attribution WS-reactive refresh | 7B.2 |
| AttributionWaterfall empty-state | 7B.2 |
| Lobby portfolio stats from analyticsApi | 7C.1 |
| Lobby WS-reactive room scorecard refresh | 7C.1 |
| /api/health/full endpoint | 7D.1 |
| SystemHealthPanel shows vault + LLM status | 7D.1 |
| Analytics page 30s auto-refresh | 7E.1 |
| All tests pass before each commit | All tasks |

---

## Execution Order

```
7A.1 → 7A.2 → 7A.3   (Dashboard track — sequential, each builds on prior)
7B.1 → 7B.2           (Analytics components — independent of Dashboard track)
7C.1                  (Lobby — independent)
7D.1                  (Health endpoint — independent)
7E.1                  (Analytics page refresh — independent)
```

**Recommended subagent split:**
- Subagent A: 7A.1 → 7A.2 → 7A.3 (Dashboard)
- Subagent B: 7B.1 → 7B.2 → 7E.1 (Analytics components)
- Subagent C: 7C.1 → 7D.1 (Lobby + Health)

**Risks:**
1. `analyticsApi.portfolio()` requires auth. Dashboard store currently has a fallback to `performanceApi.summary()`. Remove the fallback in 7A.2 — analytics endpoint is the canonical source.
2. `DailySnapshot.portfolio_value` null until agents have traded. Dashboard equity curve will show empty chart for new installs. That's correct behavior — no fake data.
3. WS-reactive re-fetch fires multiple stores. If multiple components listen to the same WS event and each triggers a fetch, there will be duplicate API calls. Acceptable at single-user scale — no dedup needed until throughput becomes measurable.
