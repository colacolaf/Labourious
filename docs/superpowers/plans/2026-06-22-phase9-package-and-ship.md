# Phase 9 — Package & Ship

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Labourious into a distributable, self-contained desktop application. The backend Python process bundles inside the Electron app (or launches alongside it), the first-run wizard is fully wired to real API calls, the user can export trade history to CSV, and there's an end-to-end smoke test that verifies the full paper trade cycle works before release.

**What already exists:**
- `frontend/src/electron-main.js` — Electron entry, already configured
- `frontend/package.json` — `electron:dev` and `electron:build` scripts present
- `frontend/src/components/Wizard/` — WelcomeStep, BrokerStep, LLMStep, AgentsStep, AllocationStep, WizardShell — all exist
- `frontend/src/stores/wizard.store.js` — wizard state
- `tests/test_e2e_smoke.py` — smoke test file exists
- Docker support: `docker-compose.yml`, `docker/Dockerfile`

**Root problems:**
1. Wizard steps exist but most are display-only. BrokerStep does not actually save credentials to vault. LLMStep does not call the LLM config API. AgentsStep does not create agents.
2. No trade history CSV export
3. `electron-main.js` does not start the Python backend process — user must start it manually
4. No E2E smoke test covering full cycle end-to-end
5. `electron:build` in `package.json` may have missing icons/entitlements for distribution

**Architecture:**
```
Phase 9 scope:
  9A — Wizard wiring: BrokerStep saves to vault; LLMStep saves config; AgentsStep creates agents; AllocationStep saves allocation
  9B — Trade CSV export: GET /api/trades/export?format=csv; frontend download button
  9C — Electron backend launch: electron-main.js spawns uvicorn subprocess; handles graceful shutdown
  9D — E2E smoke test: pytest end-to-end — create agent, start agent, wait for paper trade cycle, verify trade record created
  9E — Electron build polish: app icon, entitlements.mac.plist, package.json build config for Mac/Windows
```

**Constraints:**
- No new npm packages except `@electron-forge/cli` or `electron-builder` (already expected in package.json).
- No new Python packages. Use `subprocess` (stdlib) to launch uvicorn from Electron.
- Commit per task. `feat(9X.Y): description`.
- Run `pytest tests/ -v --asyncio-mode=auto` before backend commits.
- Wizard wiring MUST work with auth tokens — all API calls through `apiClient` with Bearer token.

---

## File Map

### Files to Modify

| File | What changes |
|------|-------------|
| `frontend/src/components/Wizard/BrokerStep.jsx` | Wire vault save via `vaultApi.setKey` for each credential field |
| `frontend/src/components/Wizard/LLMStep.jsx` | Wire LLM config save via `llmApi.patchConfig`; test LLM via `llmApi.test` |
| `frontend/src/components/Wizard/AgentsStep.jsx` | Wire agent creation via `agentsApi.create` for each configured agent |
| `frontend/src/components/Wizard/AllocationStep.jsx` | Wire allocation save via `settingsApi.patchAllocation` |
| `frontend/src/electron-main.js` | Spawn uvicorn subprocess; wait for health; graceful shutdown |
| `frontend/package.json` | Add electron-builder config: appId, productName, icon, Mac/Win targets |
| `backend/api/trades.py` | Add `GET /api/trades/export` endpoint returning CSV |
| `frontend/src/utils/api-client.js` | Add `tradesApi.export()` for file download |
| `tests/test_e2e_smoke.py` | Implement full paper trade cycle smoke test |

### Files to Create

| File | Purpose |
|------|---------|
| `frontend/build/icon.icns` | macOS app icon (512x512, placeholder if no asset) |
| `frontend/build/icon.ico` | Windows app icon |
| `frontend/build/entitlements.mac.plist` | macOS hardened runtime entitlements |
| `tests/test_trade_export.py` | CSV export endpoint test |

---

## Priority A — Wizard Wiring

### Task 9A.1: BrokerStep — save credentials to vault on wizard completion

**Files:**
- Modify: `frontend/src/components/Wizard/BrokerStep.jsx`

**Why:** BrokerStep currently collects API key + secret via input fields but does not persist them. The wizard "completes" without saving anything to vault.

- [ ] **Step 1: Read current BrokerStep.jsx**

```bash
cat frontend/src/components/Wizard/BrokerStep.jsx
```

Understand: what fields exist, how the "Next" button is wired, what store actions are called.

- [ ] **Step 2: Wire vault save**

In `BrokerStep.jsx`, on the "Next" button click handler (or equivalent), before calling `goNext()` / `nextStep()`, add:

```jsx
import { vaultApi } from '../../utils/api-client';

const handleNext = async () => {
  if (!apiKey.trim() || !apiSecret.trim()) {
    setError('API key and secret required');
    return;
  }
  setBusy(true);
  try {
    const prefix = broker.toLowerCase();  // 'alpaca', 'kraken', etc.
    await Promise.all([
      vaultApi.setKey({ key: `${prefix}_api_key`, value: apiKey.trim() }),
      vaultApi.setKey({ key: `${prefix}_secret`, value: apiSecret.trim() }),
    ]);
    goNext();
  } catch (err) {
    setError(`Failed to save credentials: ${err.message}`);
  } finally {
    setBusy(false);
  }
};
```

The exact field names and `goNext` call depend on current BrokerStep implementation — read the file first and adapt.

Mark this step skippable — if user clicks "Skip", don't call vault save, just `goNext()`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Wizard/BrokerStep.jsx
git commit -m "feat(9A.1): BrokerStep wizard saves broker credentials to vault on next"
```

---

### Task 9A.2: LLMStep — save config + test LLM

**Files:**
- Modify: `frontend/src/components/Wizard/LLMStep.jsx`

- [ ] **Step 1: Read current LLMStep.jsx**

```bash
cat frontend/src/components/Wizard/LLMStep.jsx
```

- [ ] **Step 2: Wire config save and test**

On "Next" click:
```jsx
import { llmApi, vaultApi } from '../../utils/api-client';

const handleNext = async () => {
  setBusy(true);
  try {
    // Save LLM config (provider, model, temperature)
    await llmApi.patchConfig({ provider, model, temperature });
    
    // If Claude or OpenAI key provided, save to vault
    if (provider === 'claude' && apiKey.trim()) {
      await vaultApi.setKey({ key: 'anthropic_api_key', value: apiKey.trim() });
    }
    if (provider === 'openai' && apiKey.trim()) {
      await vaultApi.setKey({ key: 'openai_api_key', value: apiKey.trim() });
    }
    
    goNext();
  } catch (err) {
    setError(`Failed to save LLM config: ${err.message}`);
  } finally {
    setBusy(false);
  }
};
```

Add an optional "Test LLM" button:
```jsx
const handleTest = async () => {
  setTesting(true);
  try {
    const result = await llmApi.test();
    setTestResult(result.status ?? 'ok');
  } catch (err) {
    setTestResult(`failed: ${err.message}`);
  } finally {
    setTesting(false);
  }
};
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Wizard/LLMStep.jsx
git commit -m "feat(9A.2): LLMStep wizard saves LLM config and API key to vault; adds test LLM button"
```

---

### Task 9A.3: AgentsStep — create agents via API

**Files:**
- Modify: `frontend/src/components/Wizard/AgentsStep.jsx`

- [ ] **Step 1: Read current AgentsStep.jsx**

```bash
cat frontend/src/components/Wizard/AgentsStep.jsx
```

- [ ] **Step 2: Wire agent creation on Next**

On "Next":
```jsx
import { agentsApi } from '../../utils/api-client';

const handleNext = async () => {
  if (selectedAgents.length === 0) { goNext(); return; }  // skip if no agents selected
  setBusy(true);
  try {
    await Promise.all(
      selectedAgents.map(a => agentsApi.create({
        name: a.name,
        symbol: a.symbol,
        room: a.room ?? 'day_trading',
        broker: wizardStore.broker ?? 'alpaca',
        agent_type: a.type ?? 'custom',
        is_paper_trading: true,  // always start paper
        execution_mode: 'human_in_loop',
        check_frequency: 300,
      }))
    );
    goNext();
  } catch (err) {
    setError(`Failed to create agents: ${err.message}`);
  } finally {
    setBusy(false);
  }
};
```

Use `Promise.allSettled` instead of `Promise.all` so partial failures don't block — log errors but allow wizard to proceed:
```jsx
const results = await Promise.allSettled(selectedAgents.map(a => agentsApi.create({...})));
const failed = results.filter(r => r.status === 'rejected');
if (failed.length > 0) {
  setError(`${failed.length} agent(s) failed to create — you can add them from Control Room`);
}
// Still proceed to next step
goNext();
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Wizard/AgentsStep.jsx
git commit -m "feat(9A.3): AgentsStep wizard creates agents via API; partial failure handled gracefully"
```

---

### Task 9A.4: AllocationStep — save allocation config

**Files:**
- Modify: `frontend/src/components/Wizard/AllocationStep.jsx`

- [ ] **Step 1: Wire allocation save on Finish**

On "Finish" / "Complete":
```jsx
import { settingsApi } from '../../utils/api-client';

const handleFinish = async () => {
  setBusy(true);
  try {
    await settingsApi.patchAllocation({
      day_trading: allocation.day ?? 10,
      swing_trading: allocation.swing ?? 30,
      long_term: allocation.longTerm ?? 60,
    });
    goNext();  // or navigate to Lobby
  } catch (err) {
    // Non-fatal — warn but proceed
    console.warn('Allocation save failed:', err.message);
    goNext();
  } finally {
    setBusy(false);
  }
};
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Wizard/AllocationStep.jsx
git commit -m "feat(9A.4): AllocationStep wizard saves capital allocation config on finish"
```

---

## Priority B — Trade CSV Export

### Task 9B.1: `GET /api/trades/export` backend endpoint

**Files:**
- Modify: `backend/api/trades.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_trade_export.py — create

import pytest

def test_trade_export_csv_returns_csv(client, auth_headers):
    """GET /api/trades/export returns CSV content-type."""
    resp = client.get("/api/trades/export", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")

def test_trade_export_csv_has_header_row(client, auth_headers):
    """CSV export has header row with expected columns."""
    resp = client.get("/api/trades/export", headers=auth_headers)
    text = resp.text
    assert "id" in text.lower() or "symbol" in text.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
pytest tests/test_trade_export.py -v --asyncio-mode=auto
```

Expected: FAIL

- [ ] **Step 3: Add export endpoint to `backend/api/trades.py`**

```python
import csv
import io
from fastapi.responses import StreamingResponse

@router.get("/export")
async def export_trades(
    format: str = Query(default="csv", enum=["csv"]),
    agent_id: Optional[int] = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    """Export trade history as CSV. Scoped to current user's agents."""
    with get_db_session(settings.DATABASE_URL) as session:
        q = (
            select(Trade)
            .join(Agent, Trade.agent_id == Agent.id)
            .where(Agent.user_id == current_user.id)
            .order_by(Trade.opened_at.desc())
        )
        if agent_id is not None:
            q = q.where(Trade.agent_id == agent_id)
        trades = session.execute(q).scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "agent_id", "symbol", "side", "status",
        "entry_price", "exit_price", "quantity", "pnl", "pnl_pct",
        "fees", "is_paper", "entry_reason", "exit_reason",
        "opened_at", "closed_at",
    ])
    for t in trades:
        writer.writerow([
            t.id, t.agent_id, t.symbol, t.side.value if t.side else "",
            t.status.value if t.status else "",
            t.entry_price, t.exit_price, t.quantity, t.pnl, t.pnl_pct,
            t.fees, t.is_paper, t.entry_reason or "", t.exit_reason or "",
            t.opened_at.isoformat() if t.opened_at else "",
            t.closed_at.isoformat() if t.closed_at else "",
        ])
    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=labourious_trades.csv"},
    )
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_trade_export.py -v --asyncio-mode=auto
```

Expected: PASS

- [ ] **Step 5: Run full suite**

```bash
pytest tests/ -v --asyncio-mode=auto -x
```

- [ ] **Step 6: Add download button to frontend**

In `frontend/src/utils/api-client.js`, add:
```javascript
export const tradesApi = {
  // ... existing
  export: (agentId = null) => {
    const params = agentId ? `?agent_id=${agentId}` : '';
    const token = localStorage.getItem('auth_access_token');
    return fetch(`${API_BASE_URL}/api/trades/export${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    }).then(r => r.blob()).then(blob => {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'labourious_trades.csv';
      a.click();
      URL.revokeObjectURL(url);
    });
  },
};
```

In `frontend/src/pages/AnalyticsPage.jsx` (or wherever trades are displayed), add a small "Export CSV" button:
```jsx
<button
  onClick={() => tradesApi.export()}
  style={{
    background: 'none', border: '1px solid var(--color-border)', color: 'var(--color-text-muted)',
    fontFamily: 'var(--font-mono)', fontSize: 'var(--font-size-xs)', cursor: 'pointer',
    padding: '2px 8px', borderRadius: 'var(--radius-sm)',
  }}
>
  Export CSV
</button>
```

- [ ] **Step 7: Commit**

```bash
git add backend/api/trades.py frontend/src/utils/api-client.js frontend/src/pages/AnalyticsPage.jsx tests/test_trade_export.py
git commit -m "feat(9B.1): GET /api/trades/export CSV endpoint; Export CSV button on Analytics page"
```

---

## Priority C — Electron Backend Launch

### Task 9C.1: electron-main.js spawns uvicorn subprocess

**Files:**
- Modify: `frontend/src/electron-main.js`

**Why:** Users currently must start the Python backend manually (`python -m backend.main`) before launching the Electron app. For a desktop app, this is unacceptable.

**Approach:** In `electron-main.js`, before creating the browser window, spawn a `uvicorn` subprocess. Poll `/api/health` until it responds (max 30s), then create the window. On app quit, kill the subprocess.

- [ ] **Step 1: Read current `electron-main.js`**

```bash
cat frontend/src/electron-main.js
```

Understand current structure — what happens in `app.whenReady()`.

- [ ] **Step 2: Add backend launch logic**

In `electron-main.js`, before `createWindow()`:

```javascript
const { spawn } = require('child_process');
const path = require('path');
const http = require('http');

let backendProcess = null;

function startBackend() {
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  
  // In dev: use system python + project venv
  // In packaged: use bundled python (requires further packaging work — see 9E)
  const pythonCmd = isDev
    ? path.join(__dirname, '../../.venv/bin/python')
    : path.join(process.resourcesPath, 'backend', 'python');
  
  const args = ['-m', 'uvicorn', 'backend.main:app', '--port', '8000', '--host', '127.0.0.1'];
  const cwd = isDev ? path.join(__dirname, '../..') : process.resourcesPath;

  backendProcess = spawn(pythonCmd, args, {
    cwd,
    stdio: ['ignore', 'pipe', 'pipe'],
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
    },
  });

  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString().trim()));
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString().trim()));
  backendProcess.on('exit', (code) => console.log(`[backend] exited with code ${code}`));
}

function waitForBackend(maxWaitMs = 30_000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const check = () => {
      http.get('http://127.0.0.1:8000/api/health', (res) => {
        if (res.statusCode === 200) { resolve(); return; }
        retry();
      }).on('error', retry);
    };
    const retry = () => {
      if (Date.now() - start > maxWaitMs) { reject(new Error('Backend failed to start within 30s')); return; }
      setTimeout(check, 500);
    };
    check();
  });
}
```

In `app.whenReady()`:
```javascript
app.whenReady().then(async () => {
  startBackend();
  try {
    await waitForBackend();
  } catch (e) {
    // Show error dialog if backend failed to start
    const { dialog } = require('electron');
    dialog.showErrorBox('Backend Failed', 'Python backend did not start. Check logs.');
  }
  createWindow();
  // ... rest of existing code
});
```

On quit:
```javascript
app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
  }
});
```

**Dev mode note:** In development (`npm run electron:dev`), the backend is usually already running. Add a check — if `/api/health` responds immediately, skip `startBackend()`:
```javascript
// In waitForBackend, if already up: resolve immediately without starting
```

Or simpler: always try to start, accept that the `spawn` will fail if port is in use (subprocess exits immediately, existing backend keeps running).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/electron-main.js
git commit -m "feat(9C.1): electron-main spawns uvicorn backend subprocess; polls /api/health before window creation"
```

---

## Priority D — E2E Smoke Test

### Task 9D.1: Full paper trade cycle smoke test

**Files:**
- Modify: `tests/test_e2e_smoke.py`

**Why:** No automated test currently verifies that a full paper trade cycle works end-to-end: create agent → start → wait for LLM decision → trade executed → trade record in DB. This is the most important test before any release.

**Approach:** Use `pytest` + `httpx` async client. Start the FastAPI app in-process (TestClient), mock the LLM to return a fixed BUY decision, mock the broker to return a filled order. Assert trade record created in DB.

- [ ] **Step 1: Read current `tests/test_e2e_smoke.py`**

```bash
cat tests/test_e2e_smoke.py
```

Understand what's already there.

- [ ] **Step 2: Write full cycle smoke test**

```python
# tests/test_e2e_smoke.py — replace or add to existing

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_paper_trade_full_cycle(client, auth_headers, db_session):
    """
    Full cycle: create agent → orchestrator run_agent → LLM returns BUY →
    risk check passes → broker places paper order → trade record in DB.
    """
    from backend.database.models import Agent, Trade, TradeStatus
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.llm.llm_router import TradeDecision

    # 1. Create agent via API
    create_resp = client.post("/api/agents", json={
        "name": "E2E Smoke Agent",
        "symbol": "AAPL",
        "broker": "alpaca",
        "room": "day_trading",
        "is_paper_trading": True,
        "execution_mode": "autonomous",  # no human approval needed
        "check_frequency": 300,
    }, headers=auth_headers)
    assert create_resp.status_code == 201, f"Agent create failed: {create_resp.json()}"
    agent_id = create_resp.json()["id"]

    # 2. Set up mocks
    vault = MagicMock()
    vault.get.return_value = "mock_key"

    from backend.database.db import get_session_factory
    from backend.config import settings
    session_factory = get_session_factory(settings.DATABASE_URL)

    orchestrator = AgentOrchestrator(vault, session_factory)
    orchestrator.scheduler = MagicMock()

    mock_decision = TradeDecision(
        action="BUY", confidence=0.85, position_size=0.05, reasoning="E2E test BUY"
    )

    mock_order = MagicMock()
    mock_order.order_id = "e2e-order-001"
    mock_order.filled_price = 185.00
    mock_order.status = "filled"

    mock_market_data = MagicMock()
    mock_market_data.price = 185.00
    mock_market_data.volume = 1_000_000
    mock_market_data.rsi = 55.0
    mock_market_data.ma20 = 182.0
    mock_market_data.ma50 = 179.0

    mock_connector = AsyncMock()
    mock_connector.get_market_data.return_value = mock_market_data
    mock_connector.place_order.return_value = mock_order
    mock_connector.get_account_balance.return_value = 100_000.0

    with patch("backend.orchestrator.agent_orchestrator.get_connector", return_value=mock_connector), \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_class:

        mock_router = AsyncMock()
        mock_router.decide.return_value = mock_decision
        mock_router_class.from_config.return_value = mock_router

        # 3. Run the agent
        await orchestrator.run_agent(agent_id)

    # 4. Assert trade record created
    from sqlalchemy import select
    session = session_factory()
    try:
        trades = session.execute(
            select(Trade).where(Trade.agent_id == agent_id)
        ).scalars().all()
        assert len(trades) >= 1, f"Expected at least 1 trade, got {len(trades)}"
        trade = trades[0]
        assert trade.symbol == "AAPL"
        assert trade.entry_price == 185.00
        assert trade.is_paper is True
    finally:
        session.close()

    # 5. Assert agent stats updated
    session = session_factory()
    try:
        agent = session.get(Agent, agent_id)
        assert agent.total_trades >= 1
    finally:
        session.close()
```

- [ ] **Step 3: Run the smoke test**

```bash
pytest tests/test_e2e_smoke.py -v --asyncio-mode=auto
```

Expected: PASS. If FAIL, debug — this is the integration test most likely to surface regressions.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e_smoke.py
git commit -m "feat(9D.1): full paper trade cycle E2E smoke test — create agent, run orchestrator, assert trade in DB"
```

---

## Priority E — Electron Build Polish

### Task 9E.1: electron-builder config + icons + Mac entitlements

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/build/entitlements.mac.plist`

**Why:** `npm run electron:build` likely produces an unsigned, icon-less app. For local distribution (not App Store), just need correct build config and a placeholder icon.

- [ ] **Step 1: Read current `frontend/package.json` build section**

```bash
cat frontend/package.json | python3 -m json.tool | grep -A 50 '"build"'
```

- [ ] **Step 2: Add/update electron-builder config in package.json**

In `frontend/package.json`, ensure the `"build"` section contains:

```json
"build": {
  "appId": "com.labourious.app",
  "productName": "Labourious",
  "copyright": "Copyright © 2026",
  "files": [
    "build/**/*",
    "src/electron-main.js",
    "src/preload.js",
    "node_modules/**/*"
  ],
  "extraResources": [
    {
      "from": "../backend",
      "to": "backend",
      "filter": ["**/*.py", "requirements.txt"]
    },
    {
      "from": "../data",
      "to": "data"
    }
  ],
  "mac": {
    "category": "public.app-category.finance",
    "icon": "build/icon.icns",
    "hardenedRuntime": true,
    "gatekeeperAssess": false,
    "entitlements": "build/entitlements.mac.plist",
    "entitlementsInherit": "build/entitlements.mac.plist",
    "target": [{"target": "dmg", "arch": ["arm64", "x64"]}]
  },
  "win": {
    "icon": "build/icon.ico",
    "target": [{"target": "nsis", "arch": ["x64"]}]
  },
  "dmg": {
    "title": "Labourious Installer"
  }
}
```

- [ ] **Step 3: Create entitlements.mac.plist**

```bash
mkdir -p frontend/build
```

Create `frontend/build/entitlements.mac.plist`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>com.apple.security.cs.allow-jit</key><true/>
  <key>com.apple.security.cs.allow-unsigned-executable-memory</key><true/>
  <key>com.apple.security.network.client</key><true/>
  <key>com.apple.security.network.server</key><true/>
</dict>
</plist>
```

- [ ] **Step 4: Create placeholder icons (if no real assets)**

```bash
# Check if icons exist
ls frontend/build/*.icns frontend/build/*.ico 2>/dev/null || echo "No icons — need to create"
```

If no icons: create a placeholder with ImageMagick if available, or document that a designer-supplied icon is needed for distribution. The build will work without icons but show a default Electron icon.

```bash
# If ImageMagick available:
convert -size 512x512 xc:"#0a0a0f" -fill "#00ff88" -font Courier-Bold -pointsize 200 -gravity center -annotate 0 "L" frontend/build/icon.png
# Then convert to .icns / .ico using electron-icon-builder or iconutil
```

If ImageMagick not available: document this as a manual step. Add placeholder files so the build doesn't fail:
```bash
touch frontend/build/icon.icns frontend/build/icon.ico
```
(Electron-builder will warn but proceed)

- [ ] **Step 5: Verify build works**

```bash
cd frontend && npm run electron:build
```

Expected: produces `dist/` with .dmg (Mac) or .exe (Windows). May warn about missing code signing — expected for local distribution.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/build/
git commit -m "feat(9E.1): electron-builder config for Mac/Windows; app icon, entitlements, extraResources for backend"
```

---

## Self-Review Checklist

| Requirement | Task |
|-------------|------|
| Wizard BrokerStep saves to vault | 9A.1 |
| Wizard LLMStep saves config + key to vault | 9A.2 |
| Wizard LLMStep test button | 9A.2 |
| Wizard AgentsStep creates agents via API | 9A.3 |
| Wizard AgentsStep: partial failure non-blocking | 9A.3 |
| Wizard AllocationStep saves allocation config | 9A.4 |
| CSV export endpoint | 9B.1 |
| CSV export auth-scoped to user's agents | 9B.1 |
| Export CSV button on Analytics page | 9B.1 |
| Electron spawns uvicorn subprocess | 9C.1 |
| Electron polls health before showing window | 9C.1 |
| Electron kills subprocess on quit | 9C.1 |
| Full paper trade cycle smoke test passes | 9D.1 |
| electron-builder config: appId, productName | 9E.1 |
| Mac entitlements.mac.plist | 9E.1 |
| Backend files bundled in extraResources | 9E.1 |

---

## Execution Order

```
9A.1 → 9A.2 → 9A.3 → 9A.4   (Wizard wiring — sequential, wizard flow is sequential)
9B.1                          (CSV export — independent)
9C.1                          (Electron launch — independent, requires no API changes)
9D.1                          (E2E smoke — independent; run after 9A to test wizard-created agents)
9E.1                          (Build polish — run last, no runtime impact)
```

**Recommended subagent split:**
- Subagent A: 9A.1 → 9A.2 → 9A.3 → 9A.4 (Wizard wiring — pure frontend)
- Subagent B: 9B.1 (CSV export — backend + frontend, isolated)
- Subagent C: 9C.1 → 9E.1 (Electron packaging — Electron-specific)
- Subagent D: 9D.1 (E2E smoke test — testing, needs backend to be settled)

**Risks:**
1. **Electron backend launch (9C.1):** The `.venv/bin/python` path is machine-specific. In dev, this works if the venv is at the project root. In packaged app, Python must be bundled — this is non-trivial (PyInstaller, py2app, or embedding a Python distribution). Phase 9 implements the dev-mode path. For production bundling, recommend using PyInstaller to produce a self-contained `backend.exe`/`backend.bin` and referencing it in `extraResources`. Document this as a known gap.

2. **Wizard wiring (9A):** The exact field names and store actions in each Wizard step component depend on the current implementation. The plan gives the pattern — the implementer MUST read each file before applying changes.

3. **E2E smoke test (9D.1):** `execution_mode: "autonomous"` bypasses human-in-loop approval. The test creates a real agent in the test DB — use the test fixture DB (conftest.py `db_session` fixture), not the production DB. Verify `conftest.py` uses a SQLite in-memory DB for tests.

4. **CSV export auth scope (9B.1):** The export joins `Trade` → `Agent` → `user_id == current_user.id`. If agents have `user_id = NULL` (legacy agents created before auth was added), they will not appear in the export. Decide: include NULL-owner agents or not. Recommendation: include them (WHERE `agent.user_id == current_user.id OR agent.user_id IS NULL`) so old paper trading data is not lost.
