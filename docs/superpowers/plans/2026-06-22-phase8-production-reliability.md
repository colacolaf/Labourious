# Phase 8 — Production Reliability

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the agent runtime for continuous unattended operation. A trading system that needs babysitting is not production. Phase 8 adds: agent crash auto-recovery (APScheduler error handler + backoff), circuit breaker (N consecutive failures → auto-pause + notify), emergency stop all agents, DB query indexes on hot paths, and a `/api/health/full` live broker ping (Phase 7 added vault/LLM status — this adds live broker connectivity test).

**What already exists:**
- `AgentOrchestrator.run_agent` catches exceptions and sets `AgentStatus.ERROR` — but leaves the APScheduler job running, so a crashed agent keeps crashing every interval
- `RiskAgent` already auto-pauses agents on drawdown/confidence — but doesn't handle repeated broker failures
- `NotificationService` + `notify_agent_paused` — works, just not called on crash recovery events
- `TradeExecutor` — has error result on broker failure but no circuit breaker counter

**Root problems:**
1. Agent ERROR → next interval fires again → crashes again → logs flood with the same error forever
2. No circuit breaker: broker transient errors (network blip, rate limit) cause immediate pause instead of retry-with-backoff
3. No "kill switch" API — user cannot stop all agents from the UI without killing the backend process
4. `trades` table has no index on `(agent_id, status)` — analytics queries scan the whole table as trade count grows
5. `daily_snapshots` has unique constraint on `(agent_id, date)` but no index — upserts do full-table scan

**Architecture:**
```
Phase 8 scope:
  8A — Crash recovery: exponential backoff for errored agents; auto-restart after N minutes
  8B — Circuit breaker: N consecutive broker errors → pause agent, notify user
  8C — Emergency stop: POST /api/agents/emergency-stop; frontend kill switch button
  8D — DB indexes: trades (agent_id, status, opened_at), daily_snapshots (agent_id, date)
  8E — Live broker ping in health: /api/health/full adds broker connectivity test
```

**Constraints:**
- No new Python packages. APScheduler already installed. No circuit breaker library needed — 10 lines of counter logic.
- No new npm packages.
- All DB changes via Alembic.
- Never log vault contents or API keys.
- Commit per task. `feat(8X.Y): description`.
- Run `pytest tests/ -v --asyncio-mode=auto` before every backend commit.

---

## File Map

### Files to Modify

| File | What changes |
|------|-------------|
| `backend/orchestrator/agent_orchestrator.py` | Crash recovery + backoff; circuit breaker counter; emergency stop handler |
| `backend/api/agents.py` | Add `POST /api/agents/emergency-stop` |
| `backend/database/models.py` | Add `consecutive_broker_errors` column to Agent |
| `backend/api/health.py` | Add live broker ping to `/api/health/full` |
| `frontend/src/pages/ControlRoom.jsx` | Emergency stop button in UI |
| `frontend/src/utils/api-client.js` | Add `agentsApi.emergencyStop` |

### Files to Create

| File | Purpose |
|------|---------|
| `alembic/versions/xxxx_add_indexes_and_broker_error_counter.py` | DB indexes + `consecutive_broker_errors` on Agent |
| `tests/test_orchestrator_reliability.py` | Crash recovery + circuit breaker tests |

---

## WebSocket Events (Phase 8 additions)

```json
// agent_crash_recovery — emitted when a crashed agent is scheduled for restart
{
  "event": "agent_crash_recovery",
  "agent_id": 1,
  "agent_name": "My Agent",
  "retry_in_seconds": 60,
  "error": "timeout on broker API"
}

// emergency_stop_all — emitted on POST /api/agents/emergency-stop
{
  "event": "emergency_stop_all",
  "stopped_count": 4,
  "timestamp": "2026-06-22T14:00:00"
}
```

---

## Priority A — Crash Recovery with Backoff

### Task 8A.1: Add `consecutive_broker_errors` to Agent model

**Files:**
- Modify: `backend/database/models.py`
- Create: Alembic migration

- [ ] **Step 1: Add column to Agent model**

In `backend/database/models.py`, add to `Agent`:
```python
    consecutive_broker_errors = Column(Integer, default=0, nullable=False)
```

- [ ] **Step 2: Generate and run migration**

```bash
cd /Users/coleadams/labourious && source .venv/bin/activate
alembic revision --autogenerate -m "add_consecutive_broker_errors_and_db_indexes"
```

In the generated migration file, also add indexes:

```python
def upgrade() -> None:
    # Add column
    op.add_column('agents', sa.Column('consecutive_broker_errors', sa.Integer(), nullable=False, server_default='0'))
    
    # Add indexes for hot-path queries
    op.create_index('ix_trades_agent_status', 'trades', ['agent_id', 'status'])
    op.create_index('ix_trades_agent_opened', 'trades', ['agent_id', 'opened_at'])
    op.create_index('ix_daily_snapshots_agent_date', 'daily_snapshots', ['agent_id', 'date'])

def downgrade() -> None:
    op.drop_index('ix_trades_agent_status', table_name='trades')
    op.drop_index('ix_trades_agent_opened', table_name='trades')
    op.drop_index('ix_daily_snapshots_agent_date', table_name='daily_snapshots')
    op.drop_column('agents', 'consecutive_broker_errors')
```

```bash
alembic upgrade head
```

- [ ] **Step 3: Commit**

```bash
git add backend/database/models.py alembic/versions/
git commit -m "feat(8A.1): add consecutive_broker_errors to Agent; DB indexes on trades and daily_snapshots"
```

---

### Task 8A.2: APScheduler error handler — skip next interval on persistent error

**Files:**
- Modify: `backend/orchestrator/agent_orchestrator.py`

**Problem:** When `run_agent` raises, the APScheduler job fires again on the next interval — usually crashing again with the same error. Result: log spam, broker rate limits hit, error status set/cleared in a loop.

**Approach (ponytail):** In the `except Exception` block at the bottom of `run_agent`, increment `consecutive_broker_errors` and reschedule the job with exponential delay (min 60s, max 3600s). Do NOT remove the job — just push the next fire time.

- [ ] **Step 1: Write failing test**

```python
# tests/test_orchestrator_reliability.py — create

import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_run_agent_backoff_on_repeated_failure():
    """Agent with consecutive_broker_errors >= 3 gets rescheduled with backoff."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    session = MagicMock()

    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.name = "TestAgent"
    agent.is_active = True
    agent.status = AgentStatus.IDLE
    agent.consecutive_broker_errors = 3  # already failed 3 times
    agent.broker = "alpaca"
    agent.is_paper_trading = True
    agent.symbol = "AAPL"
    agent.context_file_path = None
    agent.check_frequency = 300
    agent.user_id = None

    session.query.return_value.filter.return_value.first.return_value = agent

    db_factory = MagicMock(return_value=session)
    orchestrator = AgentOrchestrator(vault, db_factory)
    orchestrator.scheduler = MagicMock()

    # Force broker error
    with patch("backend.orchestrator.agent_orchestrator.get_connector", side_effect=Exception("timeout")):
        await orchestrator.run_agent(1)

    # Scheduler should have been called to reschedule with backoff
    # (Either modify_job or add_job with a future start_date)
    assert session.add.called
    assert agent.consecutive_broker_errors == 4  # incremented
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_orchestrator_reliability.py::test_run_agent_backoff_on_repeated_failure -v --asyncio-mode=auto
```

Expected: FAIL — no backoff logic yet

- [ ] **Step 3: Update `run_agent` exception handler in `agent_orchestrator.py`**

In the `except Exception` block at the bottom of `run_agent` (after the inner try/except that sets ERROR status), add backoff logic:

```python
        except Exception as e:
            logger.exception(f"agent {agent_id} fatal error: {e}")
            try:
                agent = session.query(Agent).filter(Agent.id == agent_id).first()
                if agent:
                    agent.status = AgentStatus.ERROR
                    agent.consecutive_broker_errors = (agent.consecutive_broker_errors or 0) + 1
                    session.add(agent)
                    session.commit()

                    # Exponential backoff: 60s * 2^(errors-1), cap at 3600s
                    # ponytail: simple counter backoff, replace with circuit breaker if N-broker support needs per-broker state
                    errors = agent.consecutive_broker_errors
                    backoff_seconds = min(60 * (2 ** (errors - 1)), 3600)

                    # Reschedule next run with backoff delay
                    from datetime import datetime, timedelta
                    next_run = datetime.now() + timedelta(seconds=backoff_seconds)
                    try:
                        self.scheduler.reschedule_job(
                            f"agent_{agent_id}",
                            trigger="date",
                            run_date=next_run,
                        )
                        logger.warning(
                            f"agent {agent_id} backoff: next run in {backoff_seconds}s "
                            f"(consecutive_errors={errors})"
                        )
                    except Exception as sched_e:
                        logger.error(f"agent {agent_id} backoff reschedule failed: {sched_e}")

                    await manager.broadcast({
                        "event": "agent_crash_recovery",
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "retry_in_seconds": backoff_seconds,
                        "error": str(e)[:200],
                    })
            except Exception as inner_e:
                logger.error(f"failed to handle crash for agent {agent_id}: {inner_e}")
```

Also reset `consecutive_broker_errors = 0` at the start of a **successful** run — add after `agent.last_heartbeat = datetime.utcnow()`:

```python
            agent.consecutive_broker_errors = 0  # reset on successful cycle start
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_orchestrator_reliability.py::test_run_agent_backoff_on_repeated_failure -v --asyncio-mode=auto
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator/agent_orchestrator.py tests/test_orchestrator_reliability.py
git commit -m "feat(8A.2): exponential backoff for crashed agents — reschedule with 60s*2^n delay, cap 3600s"
```

---

## Priority B — Circuit Breaker

### Task 8B.1: Circuit breaker — auto-pause agent on N consecutive broker errors

**Files:**
- Modify: `backend/orchestrator/agent_orchestrator.py`

**Threshold:** 5 consecutive broker errors → auto-pause agent and notify user. Reset counter on clean cycle.

**Why distinct from 8A.2:** 8A.2 adds backoff (reschedule delay) for any exception. 8B.1 adds a hard stop at threshold 5: agent moves to PAUSED (not ERROR), user receives notification, agent does NOT restart automatically (requires manual resume from UI).

- [ ] **Step 1: Write failing test**

```python
# tests/test_orchestrator_reliability.py — add

@pytest.mark.asyncio
async def test_circuit_breaker_pauses_agent_at_threshold():
    """Agent auto-pauses when consecutive_broker_errors reaches 5."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator, CIRCUIT_BREAKER_THRESHOLD
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    session = MagicMock()

    agent = MagicMock(spec=Agent)
    agent.id = 2
    agent.name = "CircuitTestAgent"
    agent.is_active = True
    agent.status = AgentStatus.IDLE
    agent.consecutive_broker_errors = CIRCUIT_BREAKER_THRESHOLD - 1  # one away
    agent.broker = "alpaca"
    agent.is_paper_trading = True
    agent.symbol = "AAPL"
    agent.context_file_path = None
    agent.check_frequency = 300
    agent.user_id = None

    session.query.return_value.filter.return_value.first.return_value = agent

    db_factory = MagicMock(return_value=session)
    orchestrator = AgentOrchestrator(vault, db_factory)
    orchestrator.scheduler = MagicMock()

    with patch("backend.orchestrator.agent_orchestrator.get_connector", side_effect=Exception("broker down")):
        await orchestrator.run_agent(2)

    # Agent should be PAUSED (not ERROR)
    assert agent.status == AgentStatus.PAUSED
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_orchestrator_reliability.py::test_circuit_breaker_pauses_agent_at_threshold -v --asyncio-mode=auto
```

Expected: FAIL

- [ ] **Step 3: Add circuit breaker constant and logic to `agent_orchestrator.py`**

At the top of `agent_orchestrator.py`, add:
```python
CIRCUIT_BREAKER_THRESHOLD = 5  # consecutive broker errors before auto-pause
```

In the exception handler (from 8A.2), BEFORE the backoff reschedule block, add circuit breaker check:

```python
                    # Circuit breaker: auto-pause at threshold
                    if errors >= CIRCUIT_BREAKER_THRESHOLD:
                        agent.status = AgentStatus.PAUSED
                        session.add(agent)
                        session.commit()
                        logger.warning(
                            f"agent {agent_id} circuit breaker tripped at {errors} consecutive errors — auto-paused"
                        )
                        # Remove the recurring job (agent is paused — no point retrying)
                        try:
                            self.scheduler.remove_job(f"agent_{agent_id}")
                        except Exception:
                            pass
                        # Notify user
                        if agent.user_id:
                            try:
                                from backend.notifications.triggers import notify_agent_paused
                                notify_agent_paused(
                                    agent.user_id, agent.name,
                                    f"Circuit breaker: {errors} consecutive broker failures"
                                )
                            except Exception:
                                pass
                        await manager.broadcast({
                            "event": "agent_paused",
                            "agent_id": agent.id,
                            "reason": f"circuit_breaker: {errors} consecutive errors",
                        })
                    else:
                        # Only reschedule with backoff if NOT circuit-broken
                        # (backoff code from 8A.2 goes here)
                        ...
```

Restructure the exception handler so circuit breaker check runs first, backoff only if below threshold.

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_orchestrator_reliability.py -v --asyncio-mode=auto
```

Expected: all PASS

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

- [ ] **Step 6: Commit**

```bash
git add backend/orchestrator/agent_orchestrator.py tests/test_orchestrator_reliability.py
git commit -m "feat(8B.1): circuit breaker — auto-pause agent on 5 consecutive broker failures; notify user"
```

---

## Priority C — Emergency Stop

### Task 8C.1: `POST /api/agents/emergency-stop` + UI kill switch

**Files:**
- Modify: `backend/api/agents.py`
- Modify: `frontend/src/utils/api-client.js`
- Modify: `frontend/src/pages/ControlRoom.jsx` (or `frontend/src/components/ControlRoom/RiskSection.jsx`)

**Why:** There is no way to stop all agents at once from the UI. If market gaps or API failures occur, user must kill the backend process. This is unacceptable in production.

- [ ] **Step 1: Write failing test**

```python
# tests/test_api_agents.py — add

def test_emergency_stop_pauses_all_agents(client, auth_headers, db_session, test_agent):
    """POST /api/agents/emergency-stop sets all active agents to PAUSED."""
    from backend.database.models import Agent, AgentStatus

    resp = client.post("/api/agents/emergency-stop", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "stopped" in data
    assert isinstance(data["stopped"], int)
```

- [ ] **Step 2: Add endpoint to `backend/api/agents.py`**

Add BEFORE the `/{agent_id}` routes (ordering matters — FastAPI matches in order):

```python
@router.post("/emergency-stop")
async def emergency_stop_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pause all running/idle agents immediately. Removes scheduler jobs."""
    from backend.database.models import Agent, AgentStatus
    from sqlalchemy import select
    import main as app_main  # ponytail: access orchestrator via module global

    agents = db.execute(
        select(Agent).where(Agent.is_active == True)
    ).scalars().all()

    stopped = 0
    for agent in agents:
        if agent.status in (AgentStatus.RUNNING, AgentStatus.IDLE, AgentStatus.ERROR):
            agent.status = AgentStatus.PAUSED
            db.add(agent)
            stopped += 1

    db.commit()

    # Remove all APScheduler agent jobs if orchestrator is running
    try:
        from backend.main import _orchestrator
        if _orchestrator and _orchestrator.scheduler.running:
            for agent in agents:
                try:
                    _orchestrator.scheduler.remove_job(f"agent_{agent.id}")
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"emergency stop scheduler cleanup error: {e}")

    # Broadcast
    from backend.api.websocket import manager
    from datetime import datetime
    await manager.broadcast({
        "event": "emergency_stop_all",
        "stopped_count": stopped,
        "timestamp": datetime.utcnow().isoformat(),
    })

    return {"stopped": stopped, "status": "all_agents_paused"}
```

- [ ] **Step 3: Run test**

```bash
pytest tests/test_api_agents.py::test_emergency_stop_pauses_all_agents -v --asyncio-mode=auto
```

Expected: PASS

- [ ] **Step 4: Add `agentsApi.emergencyStop` to api-client.js**

```javascript
export const agentsApi = {
  // ... existing entries
  emergencyStop: () => apiClient.post('/api/agents/emergency-stop'),
};
```

- [ ] **Step 5: Add kill switch button to RiskSection**

In `frontend/src/components/ControlRoom/RiskSection.jsx`, add emergency stop button.

Read the file first to understand current structure, then add:

```jsx
const [stopping, setStopping] = useState(false);
const [stopResult, setStopResult] = useState(null);

const handleEmergencyStop = async () => {
  if (!window.confirm('EMERGENCY STOP: pause all agents immediately?')) return;
  setStopping(true);
  try {
    const result = await agentsApi.emergencyStop();
    setStopResult(result);
  } catch (err) {
    setStopResult({ error: err.message });
  } finally {
    setStopping(false);
  }
};

// Render — place prominently at top or bottom of RiskSection:
<div style={{ borderTop: '1px solid var(--color-border)', marginTop: 'var(--space-6)', paddingTop: 'var(--space-4)' }}>
  <button
    onClick={handleEmergencyStop}
    disabled={stopping}
    style={{
      width: '100%', padding: 'var(--space-3)',
      background: stopping ? 'var(--color-bg-tertiary)' : 'var(--color-accent-danger, #ff4444)',
      color: '#fff', border: 'none', fontFamily: 'var(--font-mono)', fontWeight: 700,
      fontSize: 'var(--font-size-sm)', cursor: stopping ? 'not-allowed' : 'pointer',
      borderRadius: 'var(--radius-sm)', letterSpacing: '0.08em',
    }}
  >
    {stopping ? 'STOPPING...' : '⏹ EMERGENCY STOP ALL AGENTS'}
  </button>
  {stopResult && (
    <div style={{ marginTop: 'var(--space-2)', fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', color: stopResult.error ? 'var(--color-accent-danger)' : 'var(--color-accent-primary)' }}>
      {stopResult.error ? `Error: ${stopResult.error}` : `Stopped ${stopResult.stopped} agents.`}
    </div>
  )}
</div>
```

Import `agentsApi` at top of `RiskSection.jsx` if not already present.

- [ ] **Step 6: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/agents.py frontend/src/utils/api-client.js frontend/src/components/ControlRoom/RiskSection.jsx tests/test_api_agents.py
git commit -m "feat(8C.1): POST /api/agents/emergency-stop; kill switch button in Control Room Risk section"
```

---

## Priority D — DB Indexes (covered in 8A.1 Alembic migration)

DB indexes for `trades (agent_id, status)`, `trades (agent_id, opened_at)`, and `daily_snapshots (agent_id, date)` are created in the 8A.1 Alembic migration. No separate task needed.

---

## Priority E — Live Broker Ping in Health

### Task 8E.1: Add broker connectivity test to `/api/health/full`

**Files:**
- Modify: `backend/api/health.py`

**Why Phase 7 didn't include this:** Phase 7 added vault/LLM status to health. Broker ping requires actually calling the broker API (network I/O, potential timeout). This belongs in the reliability phase with proper timeout handling.

- [ ] **Step 1: Write failing test**

```python
# tests/test_api_health.py — add

def test_health_full_includes_broker_status(client, auth_headers):
    """GET /api/health/full returns brokers key."""
    resp = client.get("/api/health/full")
    assert resp.status_code == 200
    data = resp.json()
    assert "brokers" in data  # dict of broker_name → status
```

- [ ] **Step 2: Update `/api/health/full` to add broker pings**

In `backend/api/health.py`, in the `full_health` endpoint, add after the LLM check:

```python
    # Broker connectivity (vault-gated, 5s timeout each)
    broker_results = {}
    try:
        if settings.VAULT_PASSWORD:
            from backend.vault.encrypted_vault import EncryptedVault
            from backend.brokers.manager import get_connector, list_brokers
            import asyncio

            vault = EncryptedVault(settings.VAULT_PASSWORD)
            for broker_name in list_brokers():
                try:
                    conn = get_connector(broker_name, vault, paper=True)
                    # ponytail: 5s timeout per broker, run all in parallel
                    ok = await asyncio.wait_for(conn.test_connection(), timeout=5.0)
                    broker_results[broker_name] = "ok" if ok else "unreachable"
                except asyncio.TimeoutError:
                    broker_results[broker_name] = "timeout"
                except Exception as broker_e:
                    broker_results[broker_name] = f"error: {str(broker_e)[:40]}"
    except Exception:
        broker_results = {"error": "vault unavailable"}

    result["brokers"] = broker_results
```

**Important:** Broker ping skips vault credentials check if credentials are missing — catches `Exception` and marks "error: vault key missing". Does NOT block health endpoint.

- [ ] **Step 3: Run tests**

```bash
pytest tests/test_api_health.py -v --asyncio-mode=auto
```

Expected: PASS

- [ ] **Step 4: Update SystemHealthPanel to show broker status**

In `frontend/src/components/SystemHealthPanel.jsx`, accept `brokersStatus` prop (dict `{alpaca: "ok", binance: "timeout"}`). Render one row per broker:

```jsx
// Accept brokersStatus prop
{brokersStatus && Object.entries(brokersStatus).map(([broker, status]) => (
  <div key={broker} style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
    <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', textTransform: 'uppercase' }}>{broker}</span>
    <span style={{ color: status === 'ok' ? 'var(--color-accent-primary)' : 'var(--color-accent-danger, #ff4444)', fontSize: 'var(--font-size-xs)', fontFamily: 'var(--font-mono)' }}>
      {status.toUpperCase()}
    </span>
  </div>
))}
```

Update `dashboard.store.js fetchSystemHealth` to extract `brokersStatus` from response and store it.

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto
```

- [ ] **Step 6: Commit**

```bash
git add backend/api/health.py frontend/src/components/SystemHealthPanel.jsx frontend/src/stores/dashboard.store.js tests/test_api_health.py
git commit -m "feat(8E.1): live broker ping in /api/health/full; SystemHealthPanel shows per-broker status"
```

---

## Self-Review Checklist

| Requirement | Task |
|-------------|------|
| `consecutive_broker_errors` column on Agent | 8A.1 |
| DB indexes: trades(agent_id,status), trades(agent_id,opened_at), daily_snapshots(agent_id,date) | 8A.1 |
| Crash recovery: backoff reschedule on any exception | 8A.2 |
| Backoff resets to 0 on clean cycle | 8A.2 |
| Circuit breaker: auto-pause at 5 consecutive errors | 8B.1 |
| Circuit breaker: removes APScheduler job on trip | 8B.1 |
| Circuit breaker: notifies user via existing notification triggers | 8B.1 |
| Emergency stop endpoint | 8C.1 |
| Emergency stop: removes all scheduler jobs | 8C.1 |
| Emergency stop: broadcasts emergency_stop_all WS event | 8C.1 |
| Emergency stop: kill switch button in Risk section | 8C.1 |
| Live broker ping in health check | 8E.1 |
| Broker ping 5s timeout (no blocking) | 8E.1 |
| SystemHealthPanel shows per-broker status | 8E.1 |
| All tests pass | All tasks |

---

## Execution Order

```
8A.1 (migration — must run first, columns needed by all others)
  → 8A.2 (backoff — needs consecutive_broker_errors column)
  → 8B.1 (circuit breaker — builds on 8A.2 exception handler)
8C.1 (emergency stop — independent of A/B)
8E.1 (broker ping — independent of A/B/C)
```

**Recommended subagent split:**
- Subagent A: 8A.1 → 8A.2 → 8B.1 (backend reliability chain)
- Subagent B: 8C.1 (emergency stop — frontend + backend, independent)
- Subagent C: 8E.1 (broker ping health — independent)

**Risks:**
1. `scheduler.reschedule_job` with `trigger="date"` replaces the interval trigger. After the one-shot retry, the job does NOT reschedule back to interval automatically. Fix: in `run_agent` success path, check if job trigger is `date` (one-shot) and reschedule back to `interval` if so. Alternatively use `modify_job(next_run_time=...)` which preserves the interval trigger and just delays the next fire. Prefer `modify_job`.

   **Correction for 8A.2:** Use `scheduler.modify_job(f"agent_{agent_id}", next_run_time=next_run)` instead of `reschedule_job` with trigger="date". This delays the next interval fire without changing the trigger type.

2. `import main as app_main` in emergency stop endpoint creates a circular import risk. Use `from backend.main import _orchestrator` with a try/except instead. If the orchestrator is not initialized (vault password not set), skip scheduler cleanup gracefully.

3. Broker ping in health runs ALL broker `test_connection()` calls. If vault has no credentials for a broker, `get_connector` will pass `None` for keys — broker connector will raise immediately. Wrap in try/except as shown — no blocking.
