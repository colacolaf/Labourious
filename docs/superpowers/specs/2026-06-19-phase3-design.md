# Phase 3 Design Spec — Labourious

**Date:** 2026-06-19
**Status:** Approved for implementation
**Phase:** 3 of 3
**Focus:** Advanced Analytics + Advanced LLM integration

---

## 1. Scope Summary

Phase 3 builds on the Phase 2 agent engine (orchestrator, brokers, WebSocket, warroom) and delivers:

- **Phase 3.0** — Frontend design pre-phase: mockup options for all new UI, user picks, frozen spec before any code
- **Phase 3A** — Advanced Analytics: daily snapshot engine, performance metrics (Sharpe, drawdown, correlation, attribution), backtesting frontend, new Analytics page accessible from lobby
- **Phase 3B** — Advanced LLM: GPT-4o connector, per-agent LLM switching, cost estimation, LLM tab in AgentInspector

**Deferred to Phase 4:** Multi-user / collaboration (separate logins, shared agent libraries). Out of scope for Phase 3.

---

## 2. Architecture

### New backend modules

```
backend/
├── analytics/
│   ├── __init__.py
│   ├── snapshot_job.py      # APScheduler EOD job → writes daily_snapshots
│   ├── metrics.py           # compute_sharpe, compute_drawdown, compute_correlation, compute_attribution
│   └── cost_estimator.py    # LLM token/hr → $/month formula (Phase 3B)
├── llm/
│   └── openai_client.py     # GPT-4o via openai SDK (Phase 3B)
└── api/
    ├── analytics.py         # /api/analytics/* REST endpoints
    └── backtest_ui.py       # /api/backtest/* (trigger + poll results)
```

### New frontend components

```
frontend/src/
├── pages/
│   └── AnalyticsPage.jsx              # Route: /analytics
├── components/
│   ├── Analytics/
│   │   ├── EquityChart.jsx            # Recharts LineChart, 30d equity curve
│   │   ├── AgentLeaderboard.jsx       # Sortable table: P&L, Sharpe, win%
│   │   ├── CorrelationMatrix.jsx      # Recharts custom cell heatmap
│   │   ├── AttributionWaterfall.jsx   # Recharts BarChart waterfall variant
│   │   └── BacktestRunner.jsx         # Form + results panel
│   └── Inspector/
│       └── LLMTab.jsx                 # 6th tab in AgentInspector
```

### Existing files modified

- `backend/main.py` — register `analytics_router`, `backtest_ui_router`; add snapshot_job to scheduler startup
- `backend/llm/llm_router.py` — add OpenAI routing branch (Phase 3B)
- `frontend/src/pages/Lobby.jsx` — add 5th Analytics scorecard
- `frontend/src/components/Inspector/AgentInspector.jsx` — add 6th LLM tab (Phase 3B)
- `frontend/src/App.jsx` — add `/analytics` route

---

## 3. Database Schema (Phase 3A)

### `daily_snapshots`
```sql
CREATE TABLE daily_snapshots (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id   TEXT NOT NULL REFERENCES agents(id),
    date       DATE NOT NULL,
    total_pnl  REAL NOT NULL DEFAULT 0.0,
    daily_return_pct REAL NOT NULL DEFAULT 0.0,
    sharpe_ratio     REAL,           -- rolling 30d, NULL until 30 days of data
    max_drawdown     REAL,           -- worst peak-to-trough in period
    win_rate         REAL,           -- wins / total trades
    trade_count      INTEGER NOT NULL DEFAULT 0,
    UNIQUE(agent_id, date)
);
```

### `backtest_results`
```sql
CREATE TABLE backtest_results (
    id         TEXT PRIMARY KEY,     -- UUID
    agent_id   TEXT NOT NULL REFERENCES agents(id),
    run_at     DATETIME NOT NULL,
    start_date DATE NOT NULL,
    end_date   DATE NOT NULL,
    mode       TEXT NOT NULL,        -- 'basic' or 'walk_forward'
    status     TEXT NOT NULL,        -- 'running', 'done', 'failed'
    result_json JSON                 -- full backtest output, NULL until done
);
```

---

## 4. Analytics Computation Strategy — Option B (Daily Snapshots)

**Decision:** Daily snapshots + live intraday compute.

- APScheduler EOD job (fires at 16:05 EST daily) reads all agents' trades for the day, computes metrics, writes one row per agent to `daily_snapshots`
- Historical charts = fast reads from `daily_snapshots`
- Today's live metrics = computed fresh from `trades` table on API call
- Correlation matrix = computed from last 30d of `daily_snapshots.daily_return_pct` per agent pair

**Why not on-demand (Option A):** 500+ trades per agent over months → slow. Snapshot reads are O(1).

**Why not full cache (Option C):** Hourly recompute of everything is overkill for a local single-user app. EOD is sufficient.

---

## 5. Metrics Computation (`analytics/metrics.py`)

```python
def compute_sharpe(daily_returns: list[float], risk_free_rate: float = 0.0) -> float:
    # annualized: mean(returns) / std(returns) * sqrt(252)

def compute_max_drawdown(equity_curve: list[float]) -> float:
    # worst peak-to-trough percentage

def compute_correlation_matrix(agents_daily_returns: dict[str, list[float]]) -> dict:
    # pairwise pearson correlation, returns {agent_a: {agent_b: float}}

def compute_attribution(trades: list[Trade], date: date) -> dict:
    # returns {agent_id: pnl_contribution_pct} for a given date
```

All functions are pure (no DB calls). Tested independently. DB read/write only in `snapshot_job.py` and API layer.

---

## 6. API Endpoints (Phase 3A)

### Analytics (`/api/analytics`)

| Method | Path | Description |
|---|---|---|
| GET | `/api/analytics/portfolio` | Portfolio summary: total P&L, 30d return, YTD, Sharpe, max drawdown |
| GET | `/api/analytics/equity-curve` | `?days=30&agent_id=all` — daily equity data for chart |
| GET | `/api/analytics/leaderboard` | All agents sorted by return/Sharpe/win_rate (param: `sort_by`) |
| GET | `/api/analytics/correlation` | Pairwise correlation matrix (last 30d daily returns) |
| GET | `/api/analytics/attribution` | `?date=2026-06-19` — per-agent P&L contribution for a date |

### Backtest UI (`/api/backtest`)

| Method | Path | Description |
|---|---|---|
| POST | `/api/backtest/run` | Trigger backtest job, returns `run_id` |
| GET | `/api/backtest/{run_id}` | Poll status + results when done |
| GET | `/api/backtest/history` | `?agent_id=X` — past backtest runs for an agent |

---

## 7. Frontend Design Pre-Phase (Phase 3.0)

**Mandate:** No implementation code until designs are approved. Each task in Phase 3.0 presents ASCII mockup options. User picks. Chosen options are noted in `frontend-design-choices.md` inside this spec folder. Implementation tasks in 3A/3B reference that file.

### Task 3.0-1: Analytics Page Layout

Three options presented to user:

**Option A — Tabbed layout**
```
┌─ ANALYTICS ─────────────────────────────────────────────┐
│ [Portfolio] [Agents] [Correlation] [Attribution] [Backtest]│
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  (content of selected tab)                                  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Option B — Single-scroll sections**
```
┌─ ANALYTICS ─────────────────────────────────────────────┐
│                                                           │
│  PORTFOLIO PERFORMANCE              [30d ▼] [YTD] [ALL] │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Equity Curve (Recharts LineChart)                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │ +12.3%   │ │Sharpe1.4 │ │DD -8.3%  │ │Win 67%   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                           │
│  AGENT LEADERBOARD                    [Sort: Return ▼]  │
│  ──────────────────────────────────────────────────────  │
│  Stock Picker  +14% ██████░░  Sharpe 1.8  Win 75%       │
│  Energy Trader +10% █████░░░  Sharpe 1.3  Win 62%       │
│                                                           │
│  CORRELATION MATRIX                                       │
│  (heatmap)                                                │
│                                                           │
│  ATTRIBUTION — Today                                      │
│  (waterfall chart)                                        │
│                                                           │
│  BACKTEST                                                 │
│  (runner form + results)                                  │
│                                                           │
└─────────────────────────────────────────────────────────────┘
```

**Option C — Split pane**
```
┌─ ANALYTICS ─────────────────────────────────────────────┐
│                                                           │
│  LEFT PANEL (agent list)  │  RIGHT PANEL (detail)        │
│  ─────────────────────    │  ───────────────────────     │
│  All Agents        ✅     │  Equity curve                │
│  > Stock Picker    $14%   │  Sharpe / DD / Win stats     │
│    Energy Trader   $10%   │  Trade attribution           │
│    News Agent       $6%   │                              │
│    Index Agent      $4%   │                              │
│                           │                              │
└─────────────────────────────────────────────────────────────┘
```

### Task 3.0-2: Correlation Matrix Style

**Option A — Color heatmap**
```
         News  Energy  Stock  Index  Tech
News    [ 1.0]  [0.2]  [0.1]  [0.3]  [0.5]
Energy  [ 0.2]  [1.0]  [0.4]  [0.1]  [0.2]
Stock   [ 0.1]  [0.4]  [1.0]  [0.3]  [0.1]
Index   [ 0.3]  [0.1]  [0.3]  [1.0]  [0.2]
Tech    [ 0.5]  [0.2]  [0.1]  [0.2]  [1.0]

(cells colored: green=low corr, red=high corr)
```

**Option B — Number table only**
```
┌──────────────────────────────────────────┐
│ CORRELATION (last 30d daily returns)     │
├──────────┬──────┬────────┬──────┬───────┤
│          │ News │ Energy │Stock │ Index │
├──────────┼──────┼────────┼──────┼───────┤
│ News     │  —   │  0.18  │ 0.09 │  0.31 │
│ Energy   │ 0.18 │   —    │ 0.42 │  0.11 │
│ Stock    │ 0.09 │  0.42  │  —   │  0.28 │
│ Index    │ 0.31 │  0.11  │ 0.28 │   —   │
└──────────┴──────┴────────┴──────┴───────┘
(high correlation flagged ⚠️ > 0.7)
```

### Task 3.0-3: Attribution Chart Style

**Option A — Waterfall bar chart**
```
P&L ATTRIBUTION — 2026-06-19
                                                   
  Start  +$112,000 ─────────────────────────────
  Stock Picker      ████  +$420
  Energy Trader     ██    +$210
  News Agent        █     +$95
  Index Agent       █     +$44
  Tech Trader       ░     -$85
  End    +$112,684 ─────────────────────────────
```

**Option B — Horizontal bar (contribution %)**
```
P&L ATTRIBUTION — 2026-06-19    Total: +$684

Stock Picker   ████████████████░░░░  61.4%  +$420
Energy Trader  ████████░░░░░░░░░░░░  30.7%  +$210
News Agent     ████░░░░░░░░░░░░░░░░  13.9%   +$95
Index Agent    ██░░░░░░░░░░░░░░░░░░   6.4%   +$44
Tech Trader    ███░░░░░░░░░░░░░░░░░ -12.4%   -$85
```

### Task 3.0-4: Backtest Runner UI

**Option A — Inline panel (within Analytics page)**
```
┌─ BACKTEST ──────────────────────────────────────────────┐
│                                                          │
│  Agent:  [Energy Trader ▼]                               │
│  From:   [2024-01-01]  To: [2024-06-30]                 │
│  Mode:   ● Basic  ○ Walk-Forward                         │
│                                                          │
│  [▶ RUN BACKTEST]                                        │
│                                                          │
│  ─────────────── RESULTS ─────────────────              │
│  Return +18.5%  Win 67%  Sharpe 1.3  DD -12.4%          │
│                                                          │
│  [Equity Curve chart]                                    │
│                                                          │
│  Trade Log (table, filterable)                           │
│  [EXPORT CSV]                                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Option B — Modal triggered from AgentInspector Performance tab**
```
(In PerformanceTab.jsx)
┌─ Performance ──────────────────────────┐
│  ... live metrics ...                  │
│                                        │
│  [RUN BACKTEST ▶]  ← button            │
└────────────────────────────────────────┘

(Opens full-screen modal)
┌─ BACKTEST — Energy Trader ─────────────┐
│  From/To date pickers                  │
│  Mode selector                         │
│  [RUN]                                 │
│  Results + chart + export              │
│  [✕ CLOSE]                             │
└────────────────────────────────────────┘
```

### Task 3.0-5: Output

Write `docs/superpowers/specs/2026-06-19-phase3-frontend-design-choices.md` with all chosen options. All implementation tasks in Phase 3A/3B reference this file.

---

## 8. LLM Tab Design (Phase 3B) — Approved

```
┌─ AgentInspector ──────────────────────────────────────┐
│ [Overview][Trades][Rules][Perf][Settings][LLM]         │
├────────────────────────────────────────────────────────┤
│ LLM MODEL                                              │
│                                                        │
│ ● Ollama (Local)                                       │
│   Model: [mistral ▼]     Status: ✅ Running           │
│   Cost: Free                                           │
│                                                        │
│ ○ Claude Sonnet                                        │
│   API key: [connected via vault]                       │
│   Est. cost: ~$2.40/month  (based on check_frequency) │
│                                                        │
│ ○ GPT-4o                                               │
│   API key: [not set — configure in Control Room]       │
│   Est. cost: ~$8.10/month                              │
│                                                        │
│ [TEST LLM]  [SAVE]                                     │
└────────────────────────────────────────────────────────┘
```

Cost formula: `tokens_per_call * calls_per_month * price_per_token`
- `calls_per_month = (86400 / check_frequency) * 30`
- `tokens_per_call` estimated at 800 (prompt ~600 + response ~200)
- Prices fetched from `cost_estimator.py` constants (updated per model release)

---

## 9. OpenAI Integration (Phase 3B)

```python
# backend/llm/openai_client.py
class OpenAIClient:
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, prompt: str) -> Optional[str]:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500
        )
        return response.choices[0].message.content
```

Vault key: `openai_api_key`. Same vault convention as `anthropic_api_key`.

LLM router adds third branch:
```python
if agent.llm_provider == "openai":
    response = await self.openai.generate(prompt)
```

New `llm_provider` column added to `agents` table via Alembic migration:
```sql
ALTER TABLE agents ADD COLUMN llm_provider TEXT DEFAULT 'ollama';
-- values: 'ollama', 'claude', 'openai'
```

---

## 10. Security

All Phase 2 security requirements carry forward. Phase 3 additions:

- OpenAI API key stored in vault only (`openai_api_key`), never in DB or logs
- Cost estimator reads `check_frequency` from DB, never token counts from LLM responses (avoids log leakage)
- Backtest job: reads vault for broker keys (same as Phase 2 backtest CLI), never writes keys to disk
- Analytics endpoints: read-only; no write path exposed

---

## 11. Testing Requirements

### Phase 3A backend
- `test_metrics.py` — unit tests for all compute functions (pure functions, no DB)
- `test_snapshot_job.py` — mock DB, verify snapshot written correctly after EOD
- `test_analytics_api.py` — mock DB, verify all endpoints return correct JSON
- `test_backtest_ui.py` — mock backtest CLI, verify run/poll lifecycle

### Phase 3B backend
- `test_openai_client.py` — mock openai SDK, verify generate + error handling
- `test_cost_estimator.py` — formula correctness for each provider
- `test_llm_router_openai.py` — verify routing branch + fallback

### Frontend
- `EquityChart.test.jsx` — renders with mock data
- `AgentLeaderboard.test.jsx` — sort by each column
- `CorrelationMatrix.test.jsx` — renders cells with correct colors
- `BacktestRunner.test.jsx` — form submit → shows loading → shows results
- `LLMTab.test.jsx` — radio selection → cost estimate updates

---

## 12. Phase Structure and Estimated Duration

```
Phase 3.0 — Frontend Design     1 week   (no code, mockups + user picks)
Phase 3A  — Advanced Analytics  4 weeks
  Week 1: DB migration + analytics/metrics.py + snapshot_job.py
  Week 2: /api/analytics/* + /api/backtest/* endpoints + tests
  Week 3: Frontend — AnalyticsPage + EquityChart + AgentLeaderboard
  Week 4: Frontend — CorrelationMatrix + AttributionWaterfall + BacktestRunner
           + Lobby 5th scorecard + integration tests
Phase 3B  — Advanced LLM        2 weeks
  Week 1: openai_client.py + cost_estimator.py + DB migration + LLM routing
  Week 2: LLMTab.jsx + API endpoints + tests + integration
```

Total: ~7 weeks

---

## 13. Success Criteria

- Analytics page loads with real data within 500ms (snapshot reads, not on-demand compute)
- Correlation matrix renders for any subset of active agents
- Backtest run from UI produces same output as CLI equivalent
- LLM can be switched per-agent without restarting the backend
- Cost estimate shown in LLM tab is within 15% of actual monthly cost at steady-state check frequency
- `pytest tests/ -v` > 80% coverage on all new backend modules
- Zero API keys in logs or error messages
