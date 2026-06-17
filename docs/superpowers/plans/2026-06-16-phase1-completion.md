# Phase 1 Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add all missing Phase 1 files (tests, pages, components, stores, hooks, middleware stubs, pydantic schemas) without touching existing working code.

**Architecture:** Additive only — existing backend/main.py, db.py, vault, and frontend App.jsx/stores/api-client are left untouched. New files slot into the gaps identified in the audit. Backend tests use pytest+httpx against the real sync DB (no mocks for DB). Frontend test infrastructure is Vitest setup only.

**Tech Stack:** Python/FastAPI/SQLAlchemy (sync), pytest, pytest-asyncio, Vitest, React/CRA, Zustand

---

## File Map

**Create (backend):**
- `backend/models/__init__.py`
- `backend/models/schemas.py` — Pydantic request/response models
- `backend/models/responses.py` — Standard response wrapper
- `backend/middleware/__init__.py`
- `backend/middleware/error_handler.py` — Custom exceptions + FastAPI handlers
- `backend/api/websocket.py` — Empty stub router
- `backend/database/migrations/init.sql` — SQL schema reference
- `backend/scripts/__init__.py`
- `backend/scripts/verify_install.py` — Install verification script
- `tests/__init__.py`
- `tests/conftest.py` — pytest fixtures
- `tests/test_vault.py` — Vault encrypt/decrypt tests
- `tests/test_db.py` — DB init tests
- `tests/test_api_health.py` — Health endpoint tests

**Modify (backend):**
- `backend/requirements.txt` — add pytest, pytest-asyncio, httpx (test), python-json-logger
- `backend/main.py` — register error handlers from error_handler.py

**Create (frontend):**
- `frontend/src/pages/Lobby.jsx`
- `frontend/src/pages/WarroomDay.jsx`
- `frontend/src/pages/WarroomSwing.jsx`
- `frontend/src/pages/WarroomLongTerm.jsx`
- `frontend/src/pages/ControlRoom.jsx`
- `frontend/src/pages/NotFound.jsx`
- `frontend/src/components/PlaceholderPage.jsx`
- `frontend/src/components/Common/Header.jsx`
- `frontend/src/components/Common/Footer.jsx`
- `frontend/src/components/Common/Button.jsx`
- `frontend/src/components/Common/Modal.jsx`
- `frontend/src/components/Common/Spinner.jsx`
- `frontend/src/components/Common/Toast.jsx`
- `frontend/src/stores/ui.store.js`
- `frontend/src/stores/websocket.store.js`
- `frontend/src/stores/trades.store.js`
- `frontend/src/hooks/useAPI.js`
- `frontend/src/hooks/useWebSocket.js`
- `frontend/src/hooks/useAsync.js`
- `frontend/src/utils/formatting.js`
- `frontend/.eslintrc.json`
- `frontend/.prettierrc`
- `frontend/tests/setup.js`

---

### Task 1: Backend test dependencies

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add test deps to requirements.txt**

Open `backend/requirements.txt` and append these lines:

```
# Testing
pytest==8.3.3
pytest-asyncio==0.24.0
httpx==0.27.2
python-json-logger==2.0.7
```

> Note: `httpx` is already in requirements — just add the others. If httpx already present, skip that line.

- [ ] **Step 2: Install into venv**

```bash
source .venv/bin/activate  # or: source venv/bin/activate
pip install pytest==8.3.3 pytest-asyncio==0.24.0 python-json-logger==2.0.7
```

Expected: no errors, packages installed.

- [ ] **Step 3: Verify pytest available**

```bash
python -m pytest --version
```

Expected: `pytest 8.3.3`

- [ ] **Step 4: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add pytest, pytest-asyncio, python-json-logger to requirements"
```

---

### Task 2: Pydantic schemas

**Files:**
- Create: `backend/models/__init__.py`
- Create: `backend/models/schemas.py`
- Create: `backend/models/responses.py`

- [ ] **Step 1: Create backend/models/__init__.py**

```python
from backend.models.schemas import (
    HealthResponse,
    AgentResponse,
    TradeResponse,
    ErrorResponse,
)

__all__ = ["HealthResponse", "AgentResponse", "TradeResponse", "ErrorResponse"]
```

- [ ] **Step 2: Create backend/models/schemas.py**

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    version: str
    message: str
    timestamp: str


class AgentResponse(BaseModel):
    id: int
    name: str
    agent_type: str
    status: str
    symbol: str
    exchange: str
    is_active: bool
    is_paper_trading: bool
    total_pnl: float
    win_rate: float
    created_at: datetime

    class Config:
        from_attributes = True


class TradeResponse(BaseModel):
    id: int
    agent_id: int
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str
    opened_at: datetime
    closed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ErrorResponse(BaseModel):
    error: bool = True
    message: str
    code: str
    timestamp: datetime
```

- [ ] **Step 3: Create backend/models/responses.py**

```python
from typing import Any, Optional
from pydantic import BaseModel


class StandardResponse(BaseModel):
    success: bool = True
    data: Optional[Any] = None
    message: Optional[str] = None
```

- [ ] **Step 4: Verify import works**

```bash
python -c "from backend.models import AgentResponse, TradeResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/models/
git commit -m "feat: add pydantic request/response schemas"
```

---

### Task 3: Error handler middleware

**Files:**
- Create: `backend/middleware/__init__.py`
- Create: `backend/middleware/error_handler.py`
- Modify: `backend/main.py`

- [ ] **Step 1: Create backend/middleware/__init__.py**

```python
```

(Empty file.)

- [ ] **Step 2: Create backend/middleware/error_handler.py**

```python
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from datetime import datetime

logger = logging.getLogger("labourious")


class LabouriousError(Exception):
    pass


class VaultError(LabouriousError):
    pass


class BrokerError(LabouriousError):
    pass


class DatabaseError(LabouriousError):
    pass


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LabouriousError)
    async def labourious_error_handler(request: Request, exc: LabouriousError):
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": str(exc),
                "code": exc.__class__.__name__,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={
                "error": True,
                "message": "Internal server error",
                "code": "INTERNAL_ERROR",
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
```

- [ ] **Step 3: Register handlers in backend/main.py**

Open `backend/main.py`. After the `app.include_router(health_router)` line, add:

```python
from backend.middleware.error_handler import register_error_handlers
register_error_handlers(app)
```

The relevant section of main.py should look like:

```python
app.include_router(health_router)

from backend.middleware.error_handler import register_error_handlers
register_error_handlers(app)
```

- [ ] **Step 4: Verify import**

```bash
python -c "from backend.middleware.error_handler import LabouriousError, VaultError; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Verify app still starts**

```bash
python -m backend.main &
sleep 2
curl -s http://localhost:8000/api/health | python -m json.tool
kill %1
```

Expected: JSON with `"status": "ok"`.

- [ ] **Step 6: Commit**

```bash
git add backend/middleware/ backend/main.py
git commit -m "feat: add error handler middleware and custom exception classes"
```

---

### Task 4: WebSocket stub + migrations SQL

**Files:**
- Create: `backend/api/websocket.py`
- Create: `backend/database/migrations/init.sql`
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/verify_install.py`

- [ ] **Step 1: Create backend/api/websocket.py**

```python
from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_connect(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "WebSocket stub — Phase 2"})
    await websocket.close()
```

- [ ] **Step 2: Create backend/database/migrations/init.sql**

```sql
-- Reference schema backup — auto-managed by SQLAlchemy ORM in db.py
-- This file is for human reference only; do not run directly.

CREATE TABLE IF NOT EXISTS agents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    agent_type VARCHAR(20) NOT NULL DEFAULT 'custom',
    status VARCHAR(20) NOT NULL DEFAULT 'idle',
    symbol VARCHAR(20) NOT NULL,
    exchange VARCHAR(50) NOT NULL DEFAULT 'binance',
    timeframe VARCHAR(10) NOT NULL DEFAULT '1h',
    strategy_config JSON,
    risk_config JSON,
    max_position_size REAL DEFAULT 1000.0,
    stop_loss_pct REAL DEFAULT 2.0,
    take_profit_pct REAL DEFAULT 4.0,
    total_trades INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    total_pnl REAL DEFAULT 0.0,
    current_drawdown REAL DEFAULT 0.0,
    is_paper_trading BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME,
    last_heartbeat DATETIME
);

CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    exchange_order_id VARCHAR(100),
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    entry_price REAL NOT NULL,
    exit_price REAL,
    quantity REAL NOT NULL,
    stop_loss REAL,
    take_profit REAL,
    pnl REAL,
    pnl_pct REAL,
    fees REAL DEFAULT 0.0,
    entry_reason TEXT,
    exit_reason TEXT,
    metadata JSON,
    opened_at DATETIME NOT NULL,
    closed_at DATETIME,
    created_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    timestamp DATETIME NOT NULL,
    period VARCHAR(20) NOT NULL DEFAULT 'daily',
    portfolio_value REAL NOT NULL,
    cash_balance REAL NOT NULL,
    unrealized_pnl REAL DEFAULT 0.0,
    realized_pnl REAL DEFAULT 0.0,
    total_pnl REAL DEFAULT 0.0,
    num_trades INTEGER DEFAULT 0,
    num_wins INTEGER DEFAULT 0,
    num_losses INTEGER DEFAULT 0,
    win_rate REAL DEFAULT 0.0,
    sharpe_ratio REAL,
    sortino_ratio REAL,
    max_drawdown REAL DEFAULT 0.0,
    calmar_ratio REAL,
    metrics JSON,
    created_at DATETIME NOT NULL
);
```

- [ ] **Step 3: Create backend/scripts/__init__.py**

Empty file.

- [ ] **Step 4: Create backend/scripts/verify_install.py**

```python
#!/usr/bin/env python3
"""Run this to verify Phase 1 installation is working."""
import sys
import os


def check(label: str, fn):
    try:
        fn()
        print(f"  ✅ {label}")
        return True
    except Exception as e:
        print(f"  ❌ {label}: {e}")
        return False


def main():
    print("\n=== Labourious Install Verification ===\n")
    results = []

    results.append(check("Python >= 3.11", lambda: (
        (_ := sys.version_info) or None,
        None if sys.version_info >= (3, 11) else (_ for _ in ()).throw(RuntimeError(f"Python {sys.version_info.major}.{sys.version_info.minor} < 3.11"))
    )))

    results.append(check("fastapi importable", lambda: __import__("fastapi")))
    results.append(check("sqlalchemy importable", lambda: __import__("sqlalchemy")))
    results.append(check("cryptography importable", lambda: __import__("cryptography")))
    results.append(check("pydantic importable", lambda: __import__("pydantic")))

    results.append(check("backend.config importable", lambda: __import__("backend.config")))
    results.append(check("backend.main importable", lambda: __import__("backend.main")))
    results.append(check("backend.vault.encrypted_vault importable", lambda: __import__("backend.vault.encrypted_vault")))

    results.append(check("data/ directory exists", lambda: (
        os.makedirs("data", exist_ok=True)
    )))

    results.append(check("vault encrypt/decrypt", lambda: (
        (_ := __import__("backend.vault.encrypted_vault", fromlist=["EncryptedVault"]).EncryptedVault),
        (_ := _("TestPass#1")),
        (enc := _.encrypt_value("hello")),
        None if _.decrypt_value(enc) == "hello" else (_ for _ in ()).throw(AssertionError("mismatch"))
    )))

    ok = sum(results)
    total = len(results)
    print(f"\n{ok}/{total} checks passed")
    if ok < total:
        print("Fix failures above before proceeding to Phase 2.")
        sys.exit(1)
    else:
        print("Phase 1 installation verified ✅")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Commit**

```bash
git add backend/api/websocket.py backend/database/migrations/ backend/scripts/
git commit -m "feat: add websocket stub, migrations SQL reference, verify_install script"
```

---

### Task 5: Backend tests

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_vault.py`
- Create: `tests/test_db.py`
- Create: `tests/test_api_health.py`

- [ ] **Step 1: Create tests/__init__.py**

Empty file.

- [ ] **Step 2: Create tests/conftest.py**

```python
import pytest
import os
import tempfile
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="function")
def temp_db_path(tmp_path):
    return str(tmp_path / "test.db")


@pytest.fixture(scope="function")
def temp_vault_path(tmp_path):
    return str(tmp_path / "test_vault.db")
```

- [ ] **Step 3: Write test_vault.py**

```python
import pytest
from backend.vault.encrypted_vault import EncryptedVault, InvalidPasswordError


def test_encrypt_decrypt(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    plaintext = "BTC_API_KEY_ABC123"
    encrypted = vault.encrypt_value(plaintext)
    assert encrypted != plaintext
    decrypted = vault.decrypt_value(encrypted)
    assert decrypted == plaintext


def test_wrong_password_raises(temp_vault_path, tmp_path):
    vault1 = EncryptedVault(temp_vault_path, "Password#1")
    encrypted = vault1.encrypt_value("secret")

    vault2_path = str(tmp_path / "vault2.db")
    vault2 = EncryptedVault(vault2_path, "WrongPassword#1")
    with pytest.raises((InvalidPasswordError, ValueError)):
        vault2.decrypt_value(encrypted)


def test_set_and_get(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("api_key", "my_secret_value")
    assert vault.get("api_key") == "my_secret_value"


def test_delete_key(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("to_delete", "value")
    assert vault.has("to_delete")
    vault.delete("to_delete")
    assert not vault.has("to_delete")


def test_list_keys(temp_vault_path):
    vault = EncryptedVault(temp_vault_path, "TestPassword#1")
    vault.set("key_a", "val_a")
    vault.set("key_b", "val_b")
    keys = vault.list_keys()
    assert "key_a" in keys
    assert "key_b" in keys
```

- [ ] **Step 4: Run vault tests to verify they pass**

```bash
python -m pytest tests/test_vault.py -v
```

Expected:
```
tests/test_vault.py::test_encrypt_decrypt PASSED
tests/test_vault.py::test_wrong_password_raises PASSED
tests/test_vault.py::test_set_and_get PASSED
tests/test_vault.py::test_delete_key PASSED
tests/test_vault.py::test_list_keys PASSED
```

- [ ] **Step 5: Write test_db.py**

```python
import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.database.models import Base, Agent, Trade, Performance
from backend.database.db import init_db


def test_db_tables_created(temp_db_path):
    db_url = f"sqlite:///{temp_db_path}"
    init_db(db_url)
    assert os.path.exists(temp_db_path)

    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        tables = [row[0] for row in result]
    assert "agents" in tables
    assert "trades" in tables
    assert "performance" in tables


def test_agent_crud(temp_db_path):
    db_url = f"sqlite:///{temp_db_path}"
    init_db(db_url)

    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    session = Session()

    agent = Agent(
        name="test-agent",
        symbol="BTC/USD",
        exchange="kraken",
        timeframe="1h",
    )
    session.add(agent)
    session.commit()

    fetched = session.query(Agent).filter_by(name="test-agent").first()
    assert fetched is not None
    assert fetched.symbol == "BTC/USD"
    assert fetched.is_paper_trading is True

    session.close()
```

- [ ] **Step 6: Run db tests**

```bash
python -m pytest tests/test_db.py -v
```

Expected:
```
tests/test_db.py::test_db_tables_created PASSED
tests/test_db.py::test_agent_crud PASSED
```

- [ ] **Step 7: Write test_api_health.py**

```python
import pytest


def test_health_check_status(client):
    response = client.get("/api/health")
    assert response.status_code == 200


def test_health_check_fields(client):
    data = client.get("/api/health").json()
    assert "status" in data
    assert "version" in data
    assert "timestamp" in data


def test_health_check_ok(client):
    data = client.get("/api/health").json()
    assert data["status"] == "ok"


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "health" in data


def test_db_health_endpoint(client):
    response = client.get("/api/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
```

- [ ] **Step 8: Run all backend tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASSED (10 tests total).

- [ ] **Step 9: Commit**

```bash
git add tests/
git commit -m "test: add vault, db, and health API tests"
```

---

### Task 6: Frontend page components

**Files:**
- Create: `frontend/src/components/PlaceholderPage.jsx`
- Create: `frontend/src/pages/Lobby.jsx`
- Create: `frontend/src/pages/WarroomDay.jsx`
- Create: `frontend/src/pages/WarroomSwing.jsx`
- Create: `frontend/src/pages/WarroomLongTerm.jsx`
- Create: `frontend/src/pages/ControlRoom.jsx`
- Create: `frontend/src/pages/NotFound.jsx`

- [ ] **Step 1: Create frontend/src/components/PlaceholderPage.jsx**

```jsx
export function PlaceholderPage({ title }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      gap: 'var(--space-4)',
      color: 'var(--color-text-secondary)',
      fontFamily: 'var(--font-mono)',
    }}>
      <span style={{ fontSize: '2rem', color: 'var(--color-accent-primary)' }}>⬡</span>
      <h2 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--font-size-xl)' }}>{title}</h2>
      <p style={{ fontSize: 'var(--font-size-sm)' }}>Phase 2 implementation pending</p>
    </div>
  );
}
```

- [ ] **Step 2: Create all page files**

`frontend/src/pages/Lobby.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function Lobby() {
  return <PlaceholderPage title="Lobby — Trading Warroom" />;
}
```

`frontend/src/pages/WarroomDay.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function WarroomDay() {
  return <PlaceholderPage title="Day Trading Room" />;
}
```

`frontend/src/pages/WarroomSwing.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function WarroomSwing() {
  return <PlaceholderPage title="Swing Trading Room" />;
}
```

`frontend/src/pages/WarroomLongTerm.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function WarroomLongTerm() {
  return <PlaceholderPage title="Long-Term Investment Room" />;
}
```

`frontend/src/pages/ControlRoom.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function ControlRoom() {
  return <PlaceholderPage title="Control Room — Settings" />;
}
```

`frontend/src/pages/NotFound.jsx`:
```jsx
import { PlaceholderPage } from '../components/PlaceholderPage';
export default function NotFound() {
  return <PlaceholderPage title="404 — Page Not Found" />;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/PlaceholderPage.jsx frontend/src/pages/
git commit -m "feat: add placeholder page components for Phase 2 routes"
```

---

### Task 7: Common UI components

**Files:**
- Create: `frontend/src/components/Common/Header.jsx`
- Create: `frontend/src/components/Common/Footer.jsx`
- Create: `frontend/src/components/Common/Button.jsx`
- Create: `frontend/src/components/Common/Modal.jsx`
- Create: `frontend/src/components/Common/Spinner.jsx`
- Create: `frontend/src/components/Common/Toast.jsx`

- [ ] **Step 1: Create Header.jsx**

```jsx
export function Header() {
  return (
    <header style={{
      display: 'flex',
      alignItems: 'center',
      padding: '0 var(--space-6)',
      borderBottom: '1px solid var(--color-border)',
      background: 'var(--color-bg-secondary)',
      height: 'var(--topbar-height)',
    }}>
      <span style={{ color: 'var(--color-accent-primary)', fontFamily: 'var(--font-mono)', fontWeight: 700, letterSpacing: '0.1em' }}>
        ⬡ LABOURIOUS
      </span>
    </header>
  );
}
```

- [ ] **Step 2: Create Footer.jsx**

```jsx
export function Footer() {
  return (
    <footer style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '0 var(--space-6)',
      borderTop: '1px solid var(--color-border)',
      background: 'var(--color-bg-secondary)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-xs)',
      color: 'var(--color-text-muted)',
      height: '32px',
    }}>
      <span>Labourious v1.0.0</span>
      <span>Phase 1</span>
    </footer>
  );
}
```

- [ ] **Step 3: Create Button.jsx**

```jsx
export function Button({ children, onClick, variant = 'primary', disabled = false, style = {} }) {
  const base = {
    padding: 'var(--space-2) var(--space-4)',
    border: '1px solid',
    borderRadius: 'var(--radius-sm)',
    fontFamily: 'var(--font-mono)',
    fontSize: 'var(--font-size-sm)',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'all var(--transition-fast)',
  };

  const variants = {
    primary: {
      background: 'transparent',
      borderColor: 'var(--color-accent-primary)',
      color: 'var(--color-accent-primary)',
    },
    danger: {
      background: 'transparent',
      borderColor: 'var(--color-accent-danger)',
      color: 'var(--color-accent-danger)',
    },
    ghost: {
      background: 'transparent',
      borderColor: 'var(--color-border)',
      color: 'var(--color-text-secondary)',
    },
  };

  return (
    <button onClick={onClick} disabled={disabled} style={{ ...base, ...variants[variant], ...style }}>
      {children}
    </button>
  );
}
```

- [ ] **Step 4: Create Spinner.jsx**

```jsx
export function Spinner({ size = 20 }) {
  return (
    <div style={{
      width: size,
      height: size,
      border: `2px solid var(--color-border)`,
      borderTop: `2px solid var(--color-accent-primary)`,
      borderRadius: '50%',
      animation: 'spin 0.8s linear infinite',
    }} />
  );
}
```

- [ ] **Step 5: Create Modal.jsx**

```jsx
export function Modal({ open, onClose, title, children }) {
  if (!open) return null;
  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: 'var(--color-bg-elevated)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          padding: 'var(--space-6)',
          minWidth: 320,
          maxWidth: '90vw',
        }}
      >
        {title && (
          <h3 style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text-primary)', marginBottom: 'var(--space-4)' }}>
            {title}
          </h3>
        )}
        {children}
      </div>
    </div>
  );
}
```

- [ ] **Step 6: Create Toast.jsx**

```jsx
export function Toast({ message, type = 'info', onClose }) {
  const colors = {
    info: 'var(--color-accent-secondary)',
    success: 'var(--color-accent-success)',
    warning: 'var(--color-accent-warning)',
    error: 'var(--color-accent-danger)',
  };

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-3)',
      padding: 'var(--space-3) var(--space-4)',
      background: 'var(--color-bg-elevated)',
      border: `1px solid ${colors[type]}`,
      borderRadius: 'var(--radius-sm)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--font-size-sm)',
      color: 'var(--color-text-primary)',
    }}>
      <span style={{ color: colors[type] }}>■</span>
      <span style={{ flex: 1 }}>{message}</span>
      {onClose && (
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'var(--color-text-muted)', cursor: 'pointer' }}>
          ✕
        </button>
      )}
    </div>
  );
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/Common/
git commit -m "feat: add Header, Footer, Button, Modal, Spinner, Toast common components"
```

---

### Task 8: Remaining Zustand stores

**Files:**
- Create: `frontend/src/stores/ui.store.js`
- Create: `frontend/src/stores/websocket.store.js`
- Create: `frontend/src/stores/trades.store.js`

- [ ] **Step 1: Create ui.store.js**

```javascript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useUIStore = create(
  devtools(
    (set) => ({
      currentRoom: 'lobby',
      inspectorOpen: false,
      notifications: [],

      setCurrentRoom: (room) => set({ currentRoom: room }),
      openInspector: () => set({ inspectorOpen: true }),
      closeInspector: () => set({ inspectorOpen: false }),

      addNotification: (notif) =>
        set((state) => ({
          notifications: [
            ...state.notifications,
            { id: Date.now(), ...notif },
          ],
        })),

      removeNotification: (id) =>
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        })),

      clearNotifications: () => set({ notifications: [] }),
    }),
    { name: 'ui-store' }
  )
);
```

- [ ] **Step 2: Create websocket.store.js**

```javascript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export const useWebSocketStore = create(
  devtools(
    (set) => ({
      isConnected: false,
      lastMessage: null,
      reconnectCount: 0,

      setConnected: (connected) => set({ isConnected: connected }),
      setLastMessage: (message) => set({ lastMessage: message }),
      incrementReconnect: () =>
        set((state) => ({ reconnectCount: state.reconnectCount + 1 })),
      resetReconnect: () => set({ reconnectCount: 0 }),
    }),
    { name: 'websocket-store' }
  )
);
```

- [ ] **Step 3: Create trades.store.js**

```javascript
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import { tradesApi } from '../utils/api-client';

export const useTradesStore = create(
  devtools(
    (set) => ({
      trades: [],
      loading: false,
      error: null,

      setTrades: (trades) => set({ trades }),

      addTrade: (trade) =>
        set((state) => ({ trades: [trade, ...state.trades] })),

      fetchTrades: async (params) => {
        set({ loading: true, error: null });
        try {
          const data = await tradesApi.list(params);
          set({
            trades: Array.isArray(data) ? data : data?.items ?? [],
            loading: false,
          });
        } catch (err) {
          set({ loading: false, error: err.message });
        }
      },

      clearError: () => set({ error: null }),
    }),
    { name: 'trades-store' }
  )
);
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/stores/ui.store.js frontend/src/stores/websocket.store.js frontend/src/stores/trades.store.js
git commit -m "feat: add ui, websocket, and trades Zustand stores"
```

---

### Task 9: Frontend hooks + formatting util

**Files:**
- Create: `frontend/src/hooks/useAsync.js`
- Create: `frontend/src/hooks/useAPI.js`
- Create: `frontend/src/hooks/useWebSocket.js`
- Create: `frontend/src/utils/formatting.js`

- [ ] **Step 1: Create useAsync.js**

```javascript
import { useState, useCallback } from 'react';

export function useAsync(asyncFn) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await asyncFn(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message || 'Unknown error');
      throw err;
    } finally {
      setLoading(false);
    }
  }, [asyncFn]);

  return { loading, error, data, execute };
}
```

- [ ] **Step 2: Create useAPI.js**

```javascript
import { useState, useEffect, useCallback } from 'react';

export function useAPI(apiFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFn();
      setData(result);
    } catch (err) {
      setError(err.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch();
  }, [fetch]);

  return { data, loading, error, refetch: fetch };
}
```

- [ ] **Step 3: Create useWebSocket.js**

```javascript
import { useEffect, useRef, useCallback } from 'react';
import { useWebSocketStore } from '../stores/websocket.store';
import { WS_BASE_URL } from '../utils/constants';

export function useWebSocket(path = '/ws/connect') {
  const ws = useRef(null);
  const { setConnected, setLastMessage, incrementReconnect } = useWebSocketStore();

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    ws.current = new WebSocket(`${WS_BASE_URL}${path}`);

    ws.current.onopen = () => setConnected(true);

    ws.current.onmessage = (event) => {
      try {
        setLastMessage(JSON.parse(event.data));
      } catch {
        setLastMessage(event.data);
      }
    };

    ws.current.onclose = () => {
      setConnected(false);
      incrementReconnect();
    };

    ws.current.onerror = () => {
      setConnected(false);
    };
  }, [path, setConnected, setLastMessage, incrementReconnect]);

  useEffect(() => {
    connect();
    return () => {
      ws.current?.close();
    };
  }, [connect]);

  return { connect };
}
```

- [ ] **Step 4: Create formatting.js**

```javascript
export function formatCurrency(value, currency = 'USD', decimals = 2) {
  if (value == null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value, decimals = 2) {
  if (value == null) return '—';
  const sign = value >= 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}%`;
}

export function formatDate(date) {
  if (!date) return '—';
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function formatNumber(value, decimals = 4) {
  if (value == null) return '—';
  return Number(value).toFixed(decimals);
}

export function formatDuration(seconds) {
  if (!seconds) return '—';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/ frontend/src/utils/formatting.js
git commit -m "feat: add useAsync, useAPI, useWebSocket hooks and formatting utilities"
```

---

### Task 10: Frontend config files + test setup

**Files:**
- Create: `frontend/.eslintrc.json`
- Create: `frontend/.prettierrc`
- Create: `frontend/tests/setup.js`

- [ ] **Step 1: Create frontend/.eslintrc.json**

```json
{
  "extends": ["react-app", "react-app/jest"],
  "rules": {
    "no-console": "warn",
    "no-unused-vars": "warn"
  }
}
```

- [ ] **Step 2: Create frontend/.prettierrc**

```json
{
  "semi": true,
  "singleQuote": true,
  "tabWidth": 2,
  "trailingComma": "es5",
  "printWidth": 100
}
```

- [ ] **Step 3: Create frontend/tests/setup.js**

```javascript
// Vitest/Jest setup file for frontend tests
// Phase 1: minimal setup — no component tests yet

global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
```

- [ ] **Step 4: Verify frontend still runs**

```bash
cd frontend && npm start
```

Wait for browser to open (http://localhost:3000). Verify:
- App renders without console errors
- Header shows "⬡ LABOURIOUS"
- Sidebar nav links visible
- Main area shows placeholder content
- No red error overlays

Stop server with Ctrl+C.

- [ ] **Step 5: Commit**

```bash
git add frontend/.eslintrc.json frontend/.prettierrc frontend/tests/
git commit -m "chore: add eslint config, prettier config, and vitest setup"
```

---

### Task 11: Final verification

**Files:** None (verification only)

- [ ] **Step 1: Run all backend tests**

```bash
python -m pytest tests/ -v
```

Expected: All tests PASSED.

- [ ] **Step 2: Start backend, hit health endpoint**

```bash
python -m backend.main &
sleep 2
curl -s http://localhost:8000/api/health
curl -s http://localhost:8000/api/health/db
kill %1
```

Expected: Both return JSON with `"status": "ok"`.

- [ ] **Step 3: Run install verification script**

```bash
python backend/scripts/verify_install.py
```

Expected: All checks pass.

- [ ] **Step 4: Verify data/labourious.db created**

```bash
ls -la data/labourious.db
```

Expected: File exists.

- [ ] **Step 5: Start frontend, verify renders**

```bash
cd frontend && npm start
```

Open http://localhost:3000. Verify:
- App shell renders (header, sidebar, main area)
- Status indicator visible in header
- Navigation links present
- No console errors (open DevTools → Console)

Stop with Ctrl+C.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "chore: Phase 1 complete — all foundation components verified"
```
