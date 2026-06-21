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
