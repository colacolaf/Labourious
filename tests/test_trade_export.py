"""9B.1: Trade CSV export endpoint tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager

from backend.main import app
from backend.database.models import Base, User, UserRole, Agent, AgentStatus, Trade, TradeSide, TradeStatus
from backend.auth.utils import hash_password, create_access_token


_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_engine)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def clear_db():
    session = _Session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client():
    def override_db(database_url):
        @contextmanager
        def _ctx():
            s = _Session()
            try:
                yield s
                s.commit()
            except Exception:
                s.rollback()
                raise
            finally:
                s.close()
        return _ctx()

    import backend.api.trades as trades_module
    import backend.auth.dependencies as deps_module
    orig_db = trades_module.get_db_session
    orig_factory = deps_module.get_session_factory

    trades_module.get_db_session = override_db
    deps_module.get_session_factory = lambda url: _Session

    yield TestClient(app)

    trades_module.get_db_session = orig_db
    deps_module.get_session_factory = orig_factory


def _make_user(session):
    user = User(
        id="export_user_1",
        username="exportuser",
        email="export@example.com",
        hashed_password=hash_password("pass1234"),
        role=UserRole.TRADER,
    )
    session.add(user)
    session.commit()
    return user


def _make_agent(session, user_id):
    agent = Agent(
        user_id=user_id,
        name="Export Test Agent",
        symbol="BTC/USD",
        exchange="binance",
        timeframe="1h",
        status=AgentStatus.IDLE,
    )
    session.add(agent)
    session.commit()
    return agent


def _make_trade(session, agent_id):
    trade = Trade(
        agent_id=agent_id,
        symbol="BTC/USD",
        side=TradeSide.BUY,
        status=TradeStatus.OPEN,
        entry_price=50000.0,
        quantity=0.1,
    )
    session.add(trade)
    session.commit()
    return trade


def _token(user_id):
    return {"Authorization": f"Bearer {create_access_token({'sub': user_id})}"}


def test_export_requires_auth(client):
    resp = client.get("/api/trades/export")
    assert resp.status_code in (401, 403)


def test_export_returns_csv(client):
    session = _Session()
    user = _make_user(session)
    _make_agent(session, user.id)
    session.close()

    resp = client.get("/api/trades/export", headers=_token("export_user_1"))
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


def test_export_has_header_row(client):
    session = _Session()
    user = _make_user(session)
    _make_agent(session, user.id)
    session.close()

    resp = client.get("/api/trades/export", headers=_token("export_user_1"))
    text = resp.text
    assert "symbol" in text
    assert "entry_price" in text


def test_export_includes_trade_data(client):
    session = _Session()
    user = _make_user(session)
    agent = _make_agent(session, user.id)
    _make_trade(session, agent.id)
    session.close()

    resp = client.get("/api/trades/export", headers=_token("export_user_1"))
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    assert len(lines) >= 2  # header + at least 1 trade
    assert "BTC/USD" in resp.text


def test_export_scoped_to_user(client):
    """Other user's agents not included."""
    from datetime import datetime
    session = _Session()
    user1 = _make_user(session)
    other = User(
        id="other_user",
        username="otheruser",
        email="other@example.com",
        hashed_password=hash_password("pass1234"),
        role=UserRole.TRADER,
    )
    session.add(other)
    session.commit()
    agent2 = _make_agent(session, "other_user")
    _make_trade(session, agent2.id)
    session.close()

    resp = client.get("/api/trades/export", headers=_token("export_user_1"))
    assert resp.status_code == 200
    lines = resp.text.strip().split("\n")
    # Only header row — user1 has no trades
    assert len(lines) == 1
