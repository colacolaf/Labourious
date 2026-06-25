"""E2E smoke: register → login → agents → stop agent → token check.
Also: full paper trade cycle — create agent, run orchestrator, assert Trade in DB.
"""
import pytest
import httpx
from httpx import ASGITransport
from unittest.mock import patch, AsyncMock, MagicMock
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.database.db import init_db
from backend.database.models import Base, Trade, Agent, User, UserRole, AgentStatus
from backend.config import settings


BASE = "http://test"

TEST_USER = {"username": "smokeuser", "email": "smokeuser@example.com", "password": "SmokePass123!"}


@pytest.fixture(scope="module", autouse=True)
def _init_db(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("smoke") / "smoke.db"
    import backend.database.db as db_mod
    db_mod._engine = None
    db_mod._SessionLocal = None
    init_db(f"sqlite:///{db_path}")
    yield
    db_mod._engine = None
    db_mod._SessionLocal = None


@pytest.mark.asyncio
async def test_smoke_register_login_agents_stop():
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as client:
        # Register
        r = await client.post("/api/auth/register", json=TEST_USER)
        assert r.status_code in (201, 409), f"register: {r.text}"

        # Login
        r = await client.post("/api/auth/login", json={
            "email": TEST_USER["email"],
            "password": TEST_USER["password"],
        })
        assert r.status_code == 200, f"login: {r.text}"
        tokens = r.json()
        assert "access_token" in tokens
        access = tokens["access_token"]
        headers = {"Authorization": f"Bearer {access}"}

        # Get agents (may be empty list)
        r = await client.get("/api/agents", headers=headers)
        assert r.status_code == 200, f"agents: {r.text}"
        agents = r.json()
        assert isinstance(agents, (list, dict))

        # If agents exist, stop first one
        agent_list = agents if isinstance(agents, list) else agents.get("items", [])
        if agent_list:
            agent_id = agent_list[0]["id"]
            r = await client.post(f"/api/agents/{agent_id}/stop", headers=headers)
            assert r.status_code in (200, 404, 422), f"stop: {r.text}"

        # Verify token still valid via /me
        r = await client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200, f"me: {r.text}"

        # Invalid token → 401 or 403
        r = await client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token"})
        assert r.status_code in (401, 403), f"invalid token check: {r.text}"


# ─── 9D.1: Full paper trade cycle ────────────────────────────────────────────

_e2e_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(bind=_e2e_engine)
_e2e_Session = sessionmaker(autocommit=False, autoflush=False, bind=_e2e_engine)


@pytest.fixture(autouse=False)
def _e2e_db():
    """Isolated in-memory DB for the paper trade cycle test."""
    for table in reversed(Base.metadata.sorted_tables):
        _e2e_engine.execute = None  # handled below
    session = _e2e_Session()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()
    yield _e2e_Session


@pytest.mark.asyncio
async def test_paper_trade_full_cycle(_e2e_db):
    """
    Full cycle: create agent in DB → instantiate AgentOrchestrator →
    mock LLM (BUY 85%) + mock broker (fill at 185.00) →
    run orchestrator → assert Trade in DB with correct symbol + entry_price.
    """
    from backend.database.models import AgentStatus
    from backend.auth.utils import hash_password, create_access_token
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.llm.llm_router import TradeDecision

    Session = _e2e_db

    # Create user + agent in test DB
    session = Session()
    user = User(
        id="e2e_user_1",
        username="e2euser",
        email="e2e@example.com",
        hashed_password=hash_password("E2ePass123!"),
        role=UserRole.TRADER,
    )
    session.add(user)
    agent = Agent(
        user_id="e2e_user_1",
        name="E2E Smoke Agent",
        symbol="AAPL",
        broker="alpaca",
        exchange="binance",
        timeframe="1h",
        status=AgentStatus.IDLE,
        is_active=True,
        is_paper_trading=True,
        execution_mode="autonomous",
        check_frequency=300,
        confidence_score=75,  # above CONFIDENCE_MIN=35, avoids risk-manager pause
    )
    session.add(agent)
    session.commit()
    agent_id = agent.id
    session.close()

    # Build mock vault
    mock_vault = MagicMock()
    mock_vault.get.return_value = "mock_key"

    # Build mock connector
    mock_market = MagicMock()
    mock_market.price = 185.00
    mock_market.volume = 1_000_000
    mock_market.rsi = 55.0
    mock_market.ma20 = 182.0
    mock_market.ma50 = 179.0

    mock_connector = AsyncMock()
    mock_connector.get_market_data.return_value = mock_market
    mock_connector.get_account_balance.return_value = 100_000.0

    mock_order = MagicMock()
    mock_order.order_id = "e2e-order-001"
    mock_order.filled_price = 185.00
    mock_order.status = "filled"
    mock_connector.place_order.return_value = mock_order

    mock_decision = TradeDecision(
        action="BUY", confidence=0.85, position_size=0.05, reasoning="E2E test BUY"
    )

    mock_router = AsyncMock()
    mock_router.decide.return_value = mock_decision

    orchestrator = AgentOrchestrator(mock_vault, Session)
    orchestrator.scheduler = MagicMock()
    orchestrator.scheduler.running = False

    with patch("backend.orchestrator.agent_orchestrator.get_connector", return_value=mock_connector), \
         patch("backend.trading.trade_executor.get_connector", return_value=mock_connector), \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_cls:

        mock_router_cls.from_config.return_value = mock_router

        await orchestrator.run_agent(agent_id)

    # Assert Trade record created
    session = Session()
    trades = session.execute(select(Trade).where(Trade.agent_id == agent_id)).scalars().all()
    assert len(trades) >= 1, f"Expected >= 1 trade, got {len(trades)}"
    trade = trades[0]
    assert trade.symbol == "AAPL"
    assert trade.entry_price == 185.00
    assert trade.is_paper is True
    session.close()
