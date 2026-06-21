# Phase 4C — Notifications Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a notifications preferences UI (React) and a daily digest background job (APScheduler) to complete Phase 4B backend integration.

**Architecture:** New Zustand store mirrors the existing agents/dashboard pattern; NotificationsPage is a simple form-over-API; digest job is a synchronous APScheduler cron that queries the DB directly and calls the existing `send_daily_digest` trigger.

**Tech Stack:** React, Zustand + devtools, axios (api-client), FastAPI/APScheduler, pytest, ESLint

## Global Constraints

- CSS vars only: `var(--color-*)`, `var(--font-mono)`, `var(--space-*)`. Never hardcoded colors.
- No new npm dependencies — use React, Zustand, axios already installed.
- No new pip dependencies beyond what is in requirements.txt.
- Notifications must never raise unhandled exceptions into the trading engine.
- Never log `SMTP_PASS` or `TWILIO_AUTH_TOKEN`.
- Zustand stores must use `devtools` middleware with a `name:` string.
- All async pytest tests run with `--asyncio-mode=auto`.
- `backend.utils.logger` everywhere — never `print()`.
- TDD for backend: write failing test first, then implement.
- Frontend verification: `npm run lint` + manual browser check.

---

## File Map

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/utils/api-client.js` | Modify | Add `notificationsApi` export |
| `frontend/src/stores/notifications.store.js` | Create | Zustand store for prefs + loading/saving state |
| `frontend/src/pages/NotificationsPage.jsx` | Create | Form UI — toggles + phone_number + auth guard |
| `frontend/src/App.jsx` | Modify | Add route `/settings/notifications` + NAV_ITEMS entry |
| `backend/notifications/digest_job.py` | Create | `run_daily_digest(database_url)` synchronous cron fn |
| `backend/main.py` | Modify | Register digest scheduler in lifespan |
| `tests/test_notifications_digest.py` | Create | 4 test cases for digest_job |

---

### Task 4C.1: Notifications API Client + Zustand Store

**Files:**
- Modify: `frontend/src/utils/api-client.js`
- Create: `frontend/src/stores/notifications.store.js`

**Interfaces:**
- Produces: `notificationsApi.getPreferences()` → `Promise<PrefsObject>`, `notificationsApi.updatePreferences(patch)` → `Promise<PrefsObject>`
- Produces: `useNotificationsStore` default export with state: `{ preferences, loading, error, saving }` and actions `fetchPreferences()`, `updatePreferences(patch)`

- [ ] **Step 1: Add notificationsApi to api-client.js**

Insert before the `export default apiClient;` line:

```js
export const notificationsApi = {
  getPreferences: () => apiClient.get('/api/notifications/preferences'),
  updatePreferences: (data) => apiClient.patch('/api/notifications/preferences', data),
};
```

Note: The response interceptor already extracts `.data` from the response (line 20 in api-client.js: `(response) => response.data`). So these return the parsed object directly — no `.then(r => r.data)` needed.

- [ ] **Step 2: Create notifications.store.js**

```js
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { notificationsApi } from '../utils/api-client';

const useNotificationsStore = create(devtools((set) => ({
  preferences: null,
  loading: false,
  error: null,
  saving: false,

  fetchPreferences: async () => {
    set({ loading: true, error: null });
    try {
      const data = await notificationsApi.getPreferences();
      set({ preferences: data, loading: false });
    } catch (err) {
      set({ loading: false, error: err.message });
    }
  },

  updatePreferences: async (patch) => {
    set({ saving: true, error: null });
    try {
      const data = await notificationsApi.updatePreferences(patch);
      set({ preferences: data, saving: false });
      return data;
    } catch (err) {
      set({ saving: false, error: err.message });
      throw err;
    }
  },
}), { name: 'notifications-store' }));

export default useNotificationsStore;
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/api-client.js frontend/src/stores/notifications.store.js
git commit -m "feat(4C.1): Add notifications API client + Zustand store"
```

---

### Task 4C.2: NotificationsPage Component + Route

**Files:**
- Create: `frontend/src/pages/NotificationsPage.jsx`
- Modify: `frontend/src/App.jsx` — add import and route

**Interfaces:**
- Consumes: `useNotificationsStore` from Task 4C.1
- Consumes: `motion` from `framer-motion` (already installed) for page transition variant

- [ ] **Step 1: Create NotificationsPage.jsx**

```jsx
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import useNotificationsStore from '../stores/notifications.store';

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
};
const pageTransition = { duration: 0.18, ease: 'easeOut' };

const BOOL_FIELDS = [
  { key: 'email_enabled', label: 'Email notifications' },
  { key: 'sms_enabled', label: 'SMS notifications' },
  { key: 'notify_on_trade', label: 'Notify on trade executed' },
  { key: 'notify_on_agent_pause', label: 'Notify on agent pause' },
  { key: 'notify_on_drawdown', label: 'Notify on drawdown warning' },
  { key: 'daily_digest', label: 'Daily digest email' },
];

export default function NotificationsPage() {
  const { preferences, loading, error, saving, fetchPreferences, updatePreferences } =
    useNotificationsStore();
  const [phone, setPhone] = useState('');
  const [authError, setAuthError] = useState(false);

  useEffect(() => {
    fetchPreferences().catch((err) => {
      if (err?.status === 401 || err?.status === 403) setAuthError(true);
    });
  }, [fetchPreferences]);

  useEffect(() => {
    if (preferences?.phone_number != null) {
      setPhone(preferences.phone_number);
    }
  }, [preferences]);

  const handleToggle = (key, value) => {
    updatePreferences({ [key]: value });
  };

  const handlePhoneSave = () => {
    updatePreferences({ phone_number: phone });
  };

  if (authError) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-secondary)' }}>
        Please log in to manage notifications.
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-text-muted)' }}>
        Loading...
      </div>
    );
  }

  if (error && !preferences) {
    return (
      <div style={{ padding: 'var(--space-6)', fontFamily: 'var(--font-mono)', color: 'var(--color-accent-danger)' }}>
        Error: {error}
      </div>
    );
  }

  return (
    <motion.div
      variants={pageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={pageTransition}
      style={{
        padding: 'var(--space-6)',
        fontFamily: 'var(--font-mono)',
        maxWidth: '520px',
      }}
    >
      <h2 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xl)', marginBottom: 'var(--space-6)' }}>
        Notification Preferences
      </h2>

      {error && (
        <div style={{ color: 'var(--color-accent-danger)', fontSize: 'var(--font-size-sm)', marginBottom: 'var(--space-4)' }}>
          Error: {error}
        </div>
      )}

      {saving && (
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--font-size-xs)', marginBottom: 'var(--space-3)' }}>
          Saving...
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-4)' }}>
        {BOOL_FIELDS.map(({ key, label }) => (
          <label
            key={key}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--space-3)',
              cursor: 'pointer',
              color: 'var(--color-text-secondary)',
              fontSize: 'var(--font-size-sm)',
            }}
          >
            <input
              type="checkbox"
              checked={preferences?.[key] ?? false}
              onChange={(e) => handleToggle(key, e.target.checked)}
              style={{ accentColor: 'var(--color-accent-primary)', width: 16, height: 16 }}
            />
            {label}
          </label>
        ))}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-2)', marginTop: 'var(--space-2)' }}>
          <label style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--font-size-sm)' }}>
            Phone number (for SMS)
          </label>
          <input
            type="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            onBlur={handlePhoneSave}
            onKeyDown={(e) => e.key === 'Enter' && handlePhoneSave()}
            placeholder="+1234567890"
            style={{
              background: 'var(--color-bg-tertiary)',
              border: '1px solid var(--color-border)',
              borderRadius: '4px',
              color: 'var(--color-text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: 'var(--font-size-sm)',
              padding: 'var(--space-2) var(--space-3)',
              width: '100%',
              boxSizing: 'border-box',
            }}
          />
        </div>
      </div>
    </motion.div>
  );
}
```

- [ ] **Step 2: Add route to App.jsx**

Add import near top of App.jsx (after AnalyticsPage import):
```js
import NotificationsPage from './pages/NotificationsPage';
```

Add route inside `<Routes>` before the `<Route path="*" ...>` catch-all:
```jsx
<Route path="/settings/notifications" element={<NotificationsPage />} />
```

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 4: Manual browser check**

```bash
cd frontend && npm start
```
Navigate to `http://localhost:3000/settings/notifications`. Confirm page renders (will show auth error since no JWT is injected — that's expected and correct; auth guard is working). No console errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/NotificationsPage.jsx frontend/src/App.jsx
git commit -m "feat(4C.2): Add NotificationsPage with toggle controls"
```

---

### Task 4C.3: Sidebar Navigation Link

**Files:**
- Modify: `frontend/src/App.jsx` — add entry to `NAV_ITEMS` array

**Interfaces:**
- Consumes: existing `NAV_ITEMS` array at line 131 of App.jsx, same `NavLink` pattern

- [ ] **Step 1: Add nav item to NAV_ITEMS**

In App.jsx, find `NAV_ITEMS` array. Add Notifications entry after Settings:

```js
const NAV_ITEMS = [
  { label: 'Dashboard', path: '/', icon: '◈', end: true },
  { label: 'Day Trading', path: '/warroom/day', icon: '◉' },
  { label: 'Swing', path: '/warroom/swing', icon: '◎' },
  { label: 'Long-Term', path: '/warroom/long', icon: '◌' },
  { label: 'Analytics', path: '/analytics', icon: '◈' },
  { label: 'New Agent', path: '/agents/new', icon: '✦' },
  { label: 'Trades', path: '/trades', icon: '◇' },
  { label: 'Vault', path: '/vault', icon: '◫' },
  { label: 'Settings', path: '/settings', icon: '⊙' },
  { label: 'Notifications', path: '/settings/notifications', icon: '◆' },
];
```

- [ ] **Step 2: Run lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 3: Browser check**

`npm start` → confirm "Notifications" link appears in sidebar, clicking navigates to `/settings/notifications`.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat(4C.3): Add Notifications nav link to sidebar"
```

---

### Task 4C.4: Auth Guard on NotificationsPage

**Context:** The API returns 401 when no `Authorization: Bearer <token>` header is present. The axios interceptor in api-client.js normalizes the error and attaches `.status`. The frontend currently has no auth token flow (Phase 2), so the page will always hit 401 in dev. The guard must show a graceful message instead of crashing.

**Files:**
- Modify: `frontend/src/pages/NotificationsPage.jsx` — auth error state already wired in Task 4C.2

**Note:** Auth guard was already built into Task 4C.2 via the `authError` state:
```js
useEffect(() => {
  fetchPreferences().catch((err) => {
    if (err?.status === 401 || err?.status === 403) setAuthError(true);
  });
}, [fetchPreferences]);
```

However, the store catches errors internally and sets `error` state — it doesn't rethrow. We need to fix the fetch to detect auth errors from the store's `error` state OR rethrow from `fetchPreferences`.

- [ ] **Step 1: Update fetchPreferences in notifications.store.js to surface auth errors**

The current store swallows errors — `fetchPreferences` returns void. Update it to rethrow so the component can detect 401/403:

```js
fetchPreferences: async () => {
  set({ loading: true, error: null });
  try {
    const data = await notificationsApi.getPreferences();
    set({ preferences: data, loading: false });
  } catch (err) {
    set({ loading: false, error: err.message });
    throw err;  // rethrow so callers can detect auth errors
  }
},
```

- [ ] **Step 2: Verify NotificationsPage already handles auth error correctly**

The component already has:
```jsx
useEffect(() => {
  fetchPreferences().catch((err) => {
    if (err?.status === 401 || err?.status === 403) setAuthError(true);
  });
}, [fetchPreferences]);

if (authError) {
  return <div ...>Please log in to manage notifications.</div>;
}
```
This is already in the file from Task 4C.2. No further changes needed.

- [ ] **Step 3: Run lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 4: Browser check**

`npm start` → navigate to `/settings/notifications`. Without a valid JWT, the backend returns 401. The component shows "Please log in to manage notifications." — no crash, no blank screen.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/stores/notifications.store.js
git commit -m "feat(4C.4): Auth guard on NotificationsPage"
```

---

### Task 4C.5: Backend — Daily Digest APScheduler Job (TDD)

**Files:**
- Create: `tests/test_notifications_digest.py` — write failing tests FIRST
- Create: `backend/notifications/digest_job.py` — implement to pass tests
- Modify: `backend/main.py` — register digest scheduler

**Interfaces:**
- Consumes: `send_daily_digest(user_id: str, summary: dict)` from `backend.notifications.triggers`
- Consumes: `get_db_session(database_url)` context manager from `backend.database.db`
- Consumes: `UserNotificationPreferences`, `User`, `Agent`, `Trade`, `TradeStatus` from existing models
- Produces: `run_daily_digest(database_url: str) -> None`

**Important fix vs spec:** The spec code references `agents` before assignment. Correct version adds `agents = db.query(Agent).filter_by(user_id=prefs.user_id).all()` inside the per-user loop.

- [ ] **Step 1: Write failing tests**

Create `tests/test_notifications_digest.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.database.models import Base, User, Agent, Trade, TradeStatus, TradeSide, UserRole, AgentType, AgentStatus
from backend.notifications.models import UserNotificationPreferences


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal


@pytest.fixture
def mock_get_db_session(in_memory_db):
    @contextmanager
    def _get(database_url):
        session = in_memory_db()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("backend.notifications.digest_job.get_db_session", side_effect=_get):
        yield _get


@pytest.fixture
def mock_send_digest():
    with patch("backend.notifications.digest_job.send_daily_digest") as m:
        yield m


def _make_user(session, uid="u1", daily_digest=True):
    user = User(
        id=uid,
        username=f"user_{uid}",
        email=f"{uid}@example.com",
        hashed_password="hashed",
        role=UserRole.TRADER,
    )
    session.add(user)
    session.flush()
    prefs = UserNotificationPreferences(user_id=uid, daily_digest=daily_digest)
    session.add(prefs)
    session.commit()
    return user


def _make_agent(session, user_id, name="agent1"):
    agent = Agent(
        user_id=user_id,
        name=name,
        agent_type=AgentType.CUSTOM,
        status=AgentStatus.IDLE,
        symbol="BTC/USD",
        exchange="binance",
        timeframe="1h",
    )
    session.add(agent)
    session.commit()
    session.refresh(agent)
    return agent


def _make_trade(session, agent_id, pnl=100.0, closed_today=True):
    closed_at = datetime.utcnow() if closed_today else datetime(2000, 1, 1)
    trade = Trade(
        agent_id=agent_id,
        symbol="BTC/USD",
        side=TradeSide.BUY,
        status=TradeStatus.CLOSED,
        entry_price=50000.0,
        quantity=0.01,
        pnl=pnl,
        opened_at=datetime.utcnow(),
        closed_at=closed_at,
    )
    session.add(trade)
    session.commit()
    return trade


class TestRunDailyDigest:
    def test_fires_send_daily_digest_for_user_with_daily_digest_true(
        self, in_memory_db, mock_get_db_session, mock_send_digest
    ):
        session = in_memory_db()
        user = _make_user(session, uid="u1", daily_digest=True)
        session.close()

        from backend.notifications.digest_job import run_daily_digest
        run_daily_digest("sqlite:///:memory:")

        mock_send_digest.assert_called_once()
        call_args = mock_send_digest.call_args
        assert call_args[0][0] == "u1" or call_args[1].get("user_id") == "u1"

    def test_skips_user_with_daily_digest_false(
        self, in_memory_db, mock_get_db_session, mock_send_digest
    ):
        session = in_memory_db()
        _make_user(session, uid="u2", daily_digest=False)
        session.close()

        from backend.notifications.digest_job import run_daily_digest
        run_daily_digest("sqlite:///:memory:")

        mock_send_digest.assert_not_called()

    def test_handles_empty_trade_list(
        self, in_memory_db, mock_get_db_session, mock_send_digest
    ):
        session = in_memory_db()
        _make_user(session, uid="u3", daily_digest=True)
        # no trades added
        session.close()

        from backend.notifications.digest_job import run_daily_digest
        run_daily_digest("sqlite:///:memory:")

        mock_send_digest.assert_called_once()
        _, summary = mock_send_digest.call_args[0]
        assert summary["total_pnl"] == 0
        assert summary["trade_count"] == 0
        assert summary["best_agent"] == "N/A"
        assert summary["worst_agent"] == "N/A"

    def test_swallows_per_user_exceptions_without_crashing(
        self, in_memory_db, mock_get_db_session, mock_send_digest
    ):
        session = in_memory_db()
        _make_user(session, uid="u4", daily_digest=True)
        session.close()

        mock_send_digest.side_effect = Exception("send failed")

        from backend.notifications.digest_job import run_daily_digest
        # must not raise
        run_daily_digest("sqlite:///:memory:")
```

- [ ] **Step 2: Run tests — confirm they FAIL**

```bash
cd /Users/coleadams/labourious && pytest tests/test_notifications_digest.py -v --asyncio-mode=auto
```
Expected: `ModuleNotFoundError: No module named 'backend.notifications.digest_job'` or ImportError.

- [ ] **Step 3: Implement digest_job.py**

Create `backend/notifications/digest_job.py`:

```python
from datetime import date
from backend.database.db import get_db_session
from backend.database.models import User, Agent, Trade, TradeStatus
from backend.notifications.triggers import send_daily_digest
from backend.utils.logger import logger


def run_daily_digest(database_url: str) -> None:
    today = date.today().isoformat()
    logger.info(f"Running daily digest for {today}")
    try:
        with get_db_session(database_url) as db:
            from backend.notifications.models import UserNotificationPreferences
            prefs_list = db.query(UserNotificationPreferences).filter_by(daily_digest=True).all()
            for prefs in prefs_list:
                try:
                    user = db.query(User).filter_by(id=prefs.user_id).first()
                    if not user:
                        continue
                    agents = db.query(Agent).filter_by(user_id=prefs.user_id).all()
                    agent_ids = [a.id for a in agents]
                    trades = (
                        db.query(Trade)
                        .filter(
                            Trade.agent_id.in_(agent_ids),
                            Trade.status == TradeStatus.CLOSED,
                            Trade.closed_at >= f"{today}T00:00:00",
                        )
                        .all()
                    ) if agent_ids else []
                    total_pnl = sum(t.pnl or 0 for t in trades)
                    agent_pnl = {}
                    for t in trades:
                        agent_pnl[t.agent_id] = agent_pnl.get(t.agent_id, 0) + (t.pnl or 0)
                    best_id = max(agent_pnl, key=agent_pnl.get) if agent_pnl else None
                    worst_id = min(agent_pnl, key=agent_pnl.get) if agent_pnl else None
                    agent_map = {a.id: a.name for a in agents}
                    summary = {
                        "total_pnl": total_pnl,
                        "trade_count": len(trades),
                        "best_agent": agent_map.get(best_id, "N/A"),
                        "worst_agent": agent_map.get(worst_id, "N/A"),
                    }
                    send_daily_digest(prefs.user_id, summary)
                except Exception as e:
                    logger.error(f"digest failed for user {prefs.user_id}: {e}")
    except Exception as e:
        logger.error(f"daily digest job failed: {e}")
```

- [ ] **Step 4: Run tests — confirm they PASS**

```bash
pytest tests/test_notifications_digest.py -v --asyncio-mode=auto
```
Expected: 4 tests pass.

- [ ] **Step 5: Register digest scheduler in main.py**

In `backend/main.py`, in the `lifespan` function, add after the EOD snapshot scheduler block (after the `_snapshot_scheduler.start()` / warning block, before `yield`):

```python
    # Daily digest job (fires at 22:00 UTC)
    _digest_scheduler = None
    try:
        from backend.notifications.digest_job import run_daily_digest as _run_digest
        _digest_scheduler = AsyncIOScheduler()
        _digest_scheduler.add_job(
            _run_digest,
            trigger="cron",
            hour=22,
            minute=0,
            args=[settings.DATABASE_URL],
            id="daily_digest",
            replace_existing=True,
        )
        _digest_scheduler.start()
        logger.info("Daily digest scheduler started (22:00 UTC daily)")
    except Exception as e:
        logger.warning(f"Digest scheduler startup skipped: {e}")
```

Also add shutdown in the cleanup block after `yield`, alongside `_snapshot_scheduler`:
```python
    if _digest_scheduler and _digest_scheduler.running:
        _digest_scheduler.shutdown(wait=False)
```

Note: `_digest_scheduler` must be declared before `yield` so it's in scope after. Declare `_digest_scheduler = None` near `_snapshot_scheduler = None` at the top of lifespan.

- [ ] **Step 6: Commit**

```bash
git add backend/notifications/digest_job.py backend/main.py tests/test_notifications_digest.py
git commit -m "feat(4C.5): Add daily digest APScheduler job"
```

---

### Task 4C.6: Full Test Suite Pass

**Files:** None (verification only)

- [ ] **Step 1: Run full test suite**

```bash
cd /Users/coleadams/labourious && pytest tests/ -v --asyncio-mode=auto
```
Expected: 282+ tests pass (278 existing + 4 new digest tests). Zero failures.

- [ ] **Step 2: Review digest test coverage**

Confirm the 4 digest test cases cover:
1. `daily_digest=True` → `send_daily_digest` called
2. `daily_digest=False` → `send_daily_digest` not called
3. Empty trade list → `summary` has `total_pnl=0, trade_count=0, best_agent="N/A", worst_agent="N/A"`
4. Per-user exception → job continues without crashing

- [ ] **Step 3: Commit**

```bash
git commit -m "test(4C.6): Verify full test suite passes post-4C backend"
```
(If no additional files changed, this is a no-op commit — skip it if `git status` is clean.)

---

### Task 4C.7: Final Verification + Push

- [ ] **Step 1: Backend tests**

```bash
cd /Users/coleadams/labourious && pytest tests/ -v --asyncio-mode=auto
```
Expected: all pass.

- [ ] **Step 2: Frontend lint**

```bash
cd frontend && npm run lint
```
Expected: no errors.

- [ ] **Step 3: Frontend dev server check**

```bash
cd frontend && npm start
```
- Navigate to `/settings/notifications` — renders "Please log in" (no token) or prefs form (if token injected).
- Confirm "Notifications" link in sidebar navigates correctly.
- No console errors.

- [ ] **Step 4: Final commit if needed**

```bash
git add -p  # stage any leftover changes
git commit -m "feat(4C): Notifications frontend complete — preferences UI, daily digest job"
```

- [ ] **Step 5: Push**

```bash
git push origin main
```

---

## Self-Review

**Spec coverage:**
- 4C.1 (API client + store) → Task 4C.1 ✓
- 4C.2 (NotificationsPage) → Task 4C.2 ✓
- 4C.3 (Sidebar nav link) → Task 4C.3 ✓
- 4C.4 (Auth guard) → Task 4C.4 ✓ (wired in 4C.2, rethrow fix in 4C.4)
- 4C.5 (Digest job + tests) → Task 4C.5 ✓
- 4C.6 (Full suite pass) → Task 4C.6 ✓
- 4C.7 (Final verification + push) → Task 4C.7 ✓

**Bug fix vs spec:** Spec digest_job referenced `agents` before assignment. Fixed in Task 4C.5 Step 3 by adding `agents = db.query(Agent).filter_by(user_id=prefs.user_id).all()`.

**api-client.js response interceptor:** Interceptor at line 20 already unwraps `.data` (`(response) => response.data`). Task 4C.1 correctly omits `.then(r => r.data)`.

**`_digest_scheduler` scope:** Declared at top of lifespan alongside `_snapshot_scheduler = None` so it's accessible in shutdown block after `yield`. Task 4C.5 Step 5 explicitly calls this out.

**Auth state:** Frontend has no auth token flow yet (Phase 2 work). The auth guard shows "Please log in" gracefully — this is the correct behavior for current state.
