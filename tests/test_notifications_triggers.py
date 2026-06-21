import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.database.models import Base, User, UserRole
from backend.notifications.models import UserNotificationPreferences
from backend.notifications.triggers import (
    notify_trade_executed,
    notify_agent_paused,
    notify_drawdown_warning,
    send_daily_digest,
)


@pytest.fixture
def in_memory_db():
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal


@pytest.fixture
def mock_notification_service():
    """Mock the notification service."""
    with patch("backend.notifications.triggers.notification_service") as mock:
        yield mock


@pytest.fixture
def mock_get_db_session(in_memory_db):
    """Mock get_db_session to use in-memory DB."""
    from contextlib import contextmanager

    @contextmanager
    def _get_db_session(database_url):
        session = in_memory_db()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    with patch("backend.notifications.triggers.get_db_session", side_effect=_get_db_session):
        yield


@pytest.fixture
def setup_user_and_prefs(in_memory_db):
    """Helper to create user and notification preferences in in-memory DB."""
    def _setup(email="test@example.com", phone="+1234567890", **pref_overrides):
        session = in_memory_db()
        user = User(
            id="user-123",
            username="testuser",
            email=email,
            hashed_password="hashed_password",
            role=UserRole.TRADER,
        )
        session.add(user)
        session.flush()

        prefs_data = {
            "user_id": user.id,
            "email_enabled": True,
            "sms_enabled": False,
            "phone_number": None,
            "notify_on_trade": True,
            "notify_on_agent_pause": True,
            "notify_on_drawdown": True,
            "daily_digest": False,
        }
        prefs_data.update(pref_overrides)
        prefs = UserNotificationPreferences(**prefs_data)
        session.add(prefs)
        session.commit()
        # Detach but keep the ID and email values before closing
        user_id = user.id
        user_email = user.email
        session.close()
        return user_id, user_email, phone

    return _setup


class TestNotifyTradeExecuted:
    def test_sends_email_when_trade_enabled_and_email_enabled(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, email, _ = setup_user_and_prefs(
            email_enabled=True, notify_on_trade=True
        )
        notify_trade_executed(
            user_id=user_id,
            agent_name="TestAgent",
            symbol="BTC/USD",
            action="BUY",
            pnl=150.0,
        )
        mock_notification_service.send_email.assert_called_once()
        args, kwargs = mock_notification_service.send_email.call_args
        assert email in args

    def test_skips_notification_when_notify_on_trade_false(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, _, _ = setup_user_and_prefs(
            email_enabled=True, notify_on_trade=False
        )
        notify_trade_executed(
            user_id=user_id,
            agent_name="TestAgent",
            symbol="BTC/USD",
            action="BUY",
            pnl=150.0,
        )
        mock_notification_service.send_email.assert_not_called()

    def test_sends_sms_when_sms_enabled_and_phone_set(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        phone = "+1234567890"
        user_id, _, _ = setup_user_and_prefs(
            sms_enabled=True, phone_number=phone, notify_on_trade=True
        )
        notify_trade_executed(
            user_id=user_id,
            agent_name="TestAgent",
            symbol="BTC/USD",
            action="BUY",
            pnl=150.0,
        )
        mock_notification_service.send_sms.assert_called_once()

    def test_returns_early_when_preferences_not_found(
        self, mock_notification_service, mock_get_db_session
    ):
        notify_trade_executed(
            user_id="nonexistent-user",
            agent_name="TestAgent",
            symbol="BTC/USD",
            action="BUY",
            pnl=150.0,
        )
        mock_notification_service.send_email.assert_not_called()
        mock_notification_service.send_sms.assert_not_called()

    def test_swallows_exceptions(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, _, _ = setup_user_and_prefs(
            email_enabled=True, notify_on_trade=True
        )
        mock_notification_service.send_email.side_effect = Exception("SMTP error")
        # Should not raise
        notify_trade_executed(
            user_id=user_id,
            agent_name="TestAgent",
            symbol="BTC/USD",
            action="BUY",
            pnl=150.0,
        )


class TestNotifyAgentPaused:
    def test_sends_sms_when_sms_enabled_and_phone_set(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        phone = "+1234567890"
        user_id, _, _ = setup_user_and_prefs(
            sms_enabled=True, phone_number=phone, notify_on_agent_pause=True
        )
        notify_agent_paused(
            user_id=user_id, agent_name="TestAgent", reason="Manual pause"
        )
        mock_notification_service.send_sms.assert_called_once()
        args, kwargs = mock_notification_service.send_sms.call_args
        assert phone in args

    def test_skips_notification_when_notify_on_agent_pause_false(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        phone = "+1234567890"
        user_id, _, _ = setup_user_and_prefs(
            sms_enabled=True, phone_number=phone, notify_on_agent_pause=False
        )
        notify_agent_paused(
            user_id=user_id, agent_name="TestAgent", reason="Manual pause"
        )
        mock_notification_service.send_sms.assert_not_called()

    def test_returns_early_when_preferences_not_found(
        self, mock_notification_service, mock_get_db_session
    ):
        notify_agent_paused(
            user_id="nonexistent-user", agent_name="TestAgent", reason="Manual pause"
        )
        mock_notification_service.send_email.assert_not_called()
        mock_notification_service.send_sms.assert_not_called()


class TestNotifyDrawdownWarning:
    def test_returns_early_when_preferences_not_found(
        self, mock_notification_service, mock_get_db_session
    ):
        notify_drawdown_warning(
            user_id="nonexistent-user", agent_name="TestAgent", drawdown_pct=0.05
        )
        mock_notification_service.send_email.assert_not_called()
        mock_notification_service.send_sms.assert_not_called()

    def test_sends_email_when_drawdown_enabled_and_email_enabled(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, email, _ = setup_user_and_prefs(
            email_enabled=True, notify_on_drawdown=True
        )
        notify_drawdown_warning(
            user_id=user_id, agent_name="TestAgent", drawdown_pct=0.05
        )
        mock_notification_service.send_email.assert_called_once()
        args, kwargs = mock_notification_service.send_email.call_args
        assert email in args

    def test_skips_notification_when_notify_on_drawdown_false(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, _, _ = setup_user_and_prefs(
            email_enabled=True, notify_on_drawdown=False
        )
        notify_drawdown_warning(
            user_id=user_id, agent_name="TestAgent", drawdown_pct=0.05
        )
        mock_notification_service.send_email.assert_not_called()


class TestSendDailyDigest:
    def test_sends_email_when_daily_digest_enabled(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, email, _ = setup_user_and_prefs(
            email_enabled=True, daily_digest=True
        )
        summary = {
            "total_pnl": 250.0,
            "trade_count": 5,
            "best_agent": "Agent1",
            "worst_agent": "Agent2",
        }
        send_daily_digest(user_id=user_id, summary=summary)
        mock_notification_service.send_email.assert_called_once()
        args, kwargs = mock_notification_service.send_email.call_args
        assert email in args
        assert "Daily Trading Digest" in args[1]

    def test_skips_notification_when_daily_digest_false(
        self, mock_notification_service, mock_get_db_session, setup_user_and_prefs
    ):
        user_id, _, _ = setup_user_and_prefs(
            email_enabled=True, daily_digest=False
        )
        summary = {
            "total_pnl": 250.0,
            "trade_count": 5,
            "best_agent": "Agent1",
            "worst_agent": "Agent2",
        }
        send_daily_digest(user_id=user_id, summary=summary)
        mock_notification_service.send_email.assert_not_called()

    def test_returns_early_when_preferences_not_found(
        self, mock_notification_service, mock_get_db_session
    ):
        summary = {
            "total_pnl": 250.0,
            "trade_count": 5,
            "best_agent": "Agent1",
            "worst_agent": "Agent2",
        }
        send_daily_digest(user_id="nonexistent-user", summary=summary)
        mock_notification_service.send_email.assert_not_called()
