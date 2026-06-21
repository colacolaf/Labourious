# Phase 4B — Notifications Backend

Branch: main
Base commit: c2a07ea

## Global Constraints

- SQLAlchemy sync ORM, SQLite, sessions via `get_db_session(settings.DATABASE_URL)` context manager in `backend/database/db.py`
- Auth via `Depends(get_current_user)` from `backend/auth/dependencies.py`
- Never log vault contents or API keys — `SMTP_PASS`, `TWILIO_AUTH_TOKEN` must never appear in logs
- All API inputs validated with pydantic before use
- Error responses never expose key material
- Use `backend.utils.logger` (JSON structured) not `print()`
- Alembic for every schema change: `alembic revision --autogenerate -m "desc"` then `alembic upgrade head`
- TDD: failing test first, implement, run tests, commit
- `pytest tests/ --asyncio-mode=auto` for all tests
- All mocks via `unittest.mock.patch` — zero real network calls
- Notifications must never crash the trading engine (swallow all exceptions)

## Task 1: UserNotificationPreferences Model + Migration

**Files:**
- Create: `backend/notifications/__init__.py` (empty)
- Create: `backend/notifications/models.py`
- Modify: `backend/database/models.py` — import NotificationPreferences + add relationship to User
- Run: `alembic revision --autogenerate -m "add_notification_preferences"` then `alembic upgrade head`
- Create: `tests/test_notifications_model.py`

**Model spec (`backend/notifications/models.py`):**
```python
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database.models import Base

class UserNotificationPreferences(Base):
    __tablename__ = "user_notification_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    phone_number = Column(String(20), nullable=True)
    notify_on_trade = Column(Boolean, default=True, nullable=False)
    notify_on_agent_pause = Column(Boolean, default=True, nullable=False)
    notify_on_drawdown = Column(Boolean, default=True, nullable=False)
    daily_digest = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="notification_preferences")
```

**Add to `User` model in `backend/database/models.py`:**
```python
notification_preferences = relationship(
    "UserNotificationPreferences", back_populates="user",
    uselist=False, cascade="all, delete-orphan"
)
```

**Also import the new model in `backend/database/models.py`** so `Base.metadata` picks it up:
```python
from backend.notifications.models import UserNotificationPreferences  # noqa: F401
```

**Note on circular imports:** `backend/notifications/models.py` imports `Base` from `backend/database/models`. The import in `backend/database/models.py` of `UserNotificationPreferences` runs after `Base` is defined, so no circular import issue — but put the import at the BOTTOM of `backend/database/models.py` after all class definitions.

**Tests (write failing first):**
- `user_id` unique constraint enforced (insert duplicate user_id → IntegrityError)
- cascade delete (delete User → preferences row deleted)
- all boolean defaults correct: `email_enabled=True`, `sms_enabled=False`, `notify_on_trade=True`, `notify_on_agent_pause=True`, `notify_on_drawdown=True`, `daily_digest=False`

Use in-memory SQLite, `Base.metadata.create_all`. Use same pattern as `tests/test_auth_agent_rbac.py`.

**Commit:** `feat(4B.1): Add UserNotificationPreferences model + migration`

---

## Task 2: NotificationService (SMTP + Twilio)

**Files:**
- Create: `backend/notifications/service.py`
- Modify: `backend/config.py` — add 7 Optional[str] = None fields
- Modify: `.env.example` — add placeholder vars
- Modify: `backend/requirements.txt` — add `twilio==9.0.0` if absent
- Create: `tests/test_notifications_service.py`

**New config fields (add to `Settings` class in `backend/config.py`):**
```python
SMTP_HOST: Optional[str] = os.getenv("SMTP_HOST")
SMTP_PORT: Optional[str] = os.getenv("SMTP_PORT", "465")
SMTP_USER: Optional[str] = os.getenv("SMTP_USER")
SMTP_PASS: Optional[str] = os.getenv("SMTP_PASS")
TWILIO_ACCOUNT_SID: Optional[str] = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN: Optional[str] = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_FROM_NUMBER: Optional[str] = os.getenv("TWILIO_FROM_NUMBER")
```
Add `from typing import Optional` at top of config.py if not present.

**Service spec (`backend/notifications/service.py`):**
```python
import smtplib
from email.message import EmailMessage
from backend.config import settings
from backend.utils.logger import logger

class NotificationService:
    def __init__(self):
        self.smtp_configured = bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASS)
        self.sms_configured = bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_FROM_NUMBER)

    def send_email(self, to: str, subject: str, body: str) -> bool:
        if not self.smtp_configured:
            logger.info(f"SMTP not configured, skipping email to {to}")
            return False
        try:
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_USER
            msg["To"] = to
            msg.set_content(body)
            with smtplib.SMTP_SSL(settings.SMTP_HOST, int(settings.SMTP_PORT or 465)) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASS)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send failed to {to}: {e}")
            return False

    def send_sms(self, to: str, body: str) -> bool:
        if not self.sms_configured:
            logger.info(f"Twilio not configured, skipping SMS to {to}")
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

**Tests (mock everything — no real calls):**
- `send_email` returns False when SMTP not configured
- `send_email` returns True when SMTP configured + `smtplib.SMTP_SSL` mock accepts
- `send_email` returns False on SMTP exception
- `send_sms` returns False when Twilio not configured
- `send_sms` returns True when Twilio configured + `twilio.rest.Client` mock called
- `send_sms` returns False on Twilio exception

Patch `smtplib.SMTP_SSL` and `twilio.rest.Client`. In test setup, temporarily set `settings.SMTP_HOST`, etc. to non-None values to trigger `smtp_configured=True`. Reset after test. SMTP_PASS must not appear in log assertions.

**Commit:** `feat(4B.2): Add NotificationService (SMTP + Twilio, graceful no-op when unconfigured)`

---

## Task 3: Trigger Functions

**Files:**
- Create: `backend/notifications/triggers.py`
- Create: `tests/test_notifications_triggers.py`

**Trigger spec (`backend/notifications/triggers.py`):**
```python
from backend.config import settings
from backend.database.db import get_db_session
from backend.database.models import User
from backend.notifications.models import UserNotificationPreferences
from backend.notifications.service import NotificationService
from backend.utils.logger import logger

notification_service = NotificationService()  # module-level singleton

def notify_trade_executed(user_id: str, agent_name: str, symbol: str, action: str, pnl: float) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_trade:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Trade Executed: {action} {symbol}"
            body = f"Agent {agent_name} executed {action} on {symbol}. PnL: {pnl:.2f}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_trade_executed failed: {e}")

def notify_agent_paused(user_id: str, agent_name: str, reason: str) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_agent_pause:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Agent Paused: {agent_name}"
            body = f"Agent {agent_name} was paused. Reason: {reason}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_agent_paused failed: {e}")

def notify_drawdown_warning(user_id: str, agent_name: str, drawdown_pct: float) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_drawdown:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Drawdown Warning: {agent_name}"
            body = f"Agent {agent_name} drawdown at {drawdown_pct:.1%}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_drawdown_warning failed: {e}")

def send_daily_digest(user_id: str, summary: dict) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.daily_digest:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = "Daily Trading Digest"
            body = (
                f"Daily Summary\n"
                f"Total PnL: {summary.get('total_pnl', 0):.2f}\n"
                f"Trades: {summary.get('trade_count', 0)}\n"
                f"Best Agent: {summary.get('best_agent', 'N/A')}\n"
                f"Worst Agent: {summary.get('worst_agent', 'N/A')}"
            )
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"send_daily_digest failed: {e}")
```

**Tests (mock `notification_service.send_email` + `send_sms`, use in-memory DB):**
- `notify_trade_executed` calls `send_email` when `email_enabled=True` and `notify_on_trade=True`
- `notify_trade_executed` skips `send_email` when `notify_on_trade=False`
- `notify_agent_paused` calls `send_sms` when `sms_enabled=True` and `phone_number` set
- `notify_drawdown_warning` returns early (no crash) when preferences row not found
- `send_daily_digest` only calls `send_email` when `daily_digest=True`
- All triggers swallow exceptions — never raise

Use `unittest.mock.patch("backend.notifications.triggers.notification_service.send_email")` etc. Override `get_db_session` to use in-memory DB.

**Commit:** `feat(4B.3): Add notification trigger functions`

---

## Task 4: Notifications Router

**Files:**
- Create: `backend/notifications/router.py`
- Modify: `backend/main.py` — import and register router
- Create: `tests/test_notifications_api.py`

**Router spec (`backend/notifications/router.py`):**
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from typing import Optional
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_user, _get_db
from backend.database.models import User
from backend.notifications.models import UserNotificationPreferences

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    email_enabled: bool
    sms_enabled: bool
    phone_number: Optional[str]
    notify_on_trade: bool
    notify_on_agent_pause: bool
    notify_on_drawdown: bool
    daily_digest: bool

class PreferencesUpdate(BaseModel):
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    phone_number: Optional[str] = None
    notify_on_trade: Optional[bool] = None
    notify_on_agent_pause: Optional[bool] = None
    notify_on_drawdown: Optional[bool] = None
    daily_digest: Optional[bool] = None

@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    prefs = db.query(UserNotificationPreferences).filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs

@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(_get_db),
):
    prefs = db.query(UserNotificationPreferences).filter_by(user_id=current_user.id).first()
    if not prefs:
        prefs = UserNotificationPreferences(user_id=current_user.id)
        db.add(prefs)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)
    db.commit()
    db.refresh(prefs)
    return prefs
```

**Register in `backend/main.py`:**
```python
from backend.notifications.router import router as notifications_router
# ...
app.include_router(notifications_router)
```

**Tests:**
- GET creates default preferences if none exist → 200, defaults correct
- GET returns existing preferences → 200, values match
- PATCH updates only supplied fields, leaves others unchanged
- PATCH with empty body `{}` changes nothing
- GET without token → 403 (HTTPBearer raises 403 when no token)
- PATCH without token → 403
- PATCH `phone_number` to `null` clears it (use `exclude_none=False` behavior — see note below)

**Note on PATCH null:** `phone_number: null` in JSON body should clear the field. Use `model_dump(exclude_unset=True)` instead of `exclude_none=True` so explicit null values pass through. Adjust the PATCH handler accordingly.

**Commit:** `feat(4B.4): Add notifications preferences endpoints (GET/PATCH)`

---

## Task 5: Wire Triggers into Trading Engine

**Files:**
- Modify: `backend/orchestrator/agent_orchestrator.py` — call `notify_agent_paused` when agent paused
- Modify: `backend/trading/trade_executor.py` — call `notify_trade_executed` after trade recorded
- Modify: `backend/trading/risk_manager.py` — call `notify_drawdown_warning` when drawdown exceeded

**Rules:**
- Wrap every trigger call in `try/except Exception: pass`
- Skip if `agent.user_id is None`
- Lazy import triggers to avoid circular imports

**In `agent_orchestrator.py`** — find where `AgentStatus.PAUSED` is set (consecutive losses or risk check), add:
```python
try:
    if agent.user_id:
        from backend.notifications.triggers import notify_agent_paused
        notify_agent_paused(agent.user_id, agent.name, reason)
except Exception:
    pass
```

**In `trade_executor.py`** — after trade record is committed to DB, add:
```python
try:
    if agent_config.get("user_id"):
        from backend.notifications.triggers import notify_trade_executed
        notify_trade_executed(
            user_id=agent_config["user_id"],
            agent_name=agent_config.get("name", ""),
            symbol=symbol,
            action=decision.action,
            pnl=0.0,  # pnl not yet known at execution time
        )
except Exception:
    pass
```

**In `risk_manager.py`** — `check_agent_risk` is a pure function (no DB/user_id). The drawdown trigger must be called from the caller (orchestrator) not inside `check_agent_risk`. In `agent_orchestrator.py`, after calling `check_agent_risk`, if `should_pause` and reason contains "drawdown", also fire `notify_drawdown_warning`.

**Tests:** Update `tests/test_agent_orchestrator.py` and `tests/test_trade_executor.py`:
- Verify trigger called when `agent.user_id` is set (mock the trigger function)
- Verify trigger NOT called when `user_id` is None

**Commit:** `feat(4B.5): Wire notification triggers into trading engine`

---

## Task 6–7: Full Test Coverage Pass

**Files:** Modify existing test files as needed.

**Checklist:**
- Every trigger: test "skip" path (pref disabled, no prefs row, user_id=None)
- NotificationService: both configured and unconfigured states covered
- Router: no prefs row, partial update, auth missing
- All mocks via `unittest.mock.patch` — zero real network calls

Run: `pytest tests/test_notifications*.py -v` — all pass.

**Commit:** `test(4B.6-4B.7): Complete notification test coverage`

---

## Task 8: Final Verification

Run: `pytest tests/ -v --asyncio-mode=auto`

All tests pass (240+ expected).

**Commit:** `feat(4B): Notifications backend complete — preferences, SMTP/Twilio, triggers`
