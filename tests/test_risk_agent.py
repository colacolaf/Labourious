"""Tests for RiskAgent portfolio monitoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.orchestrator.risk_agent import RiskAgent
from backend.database.models import Agent, AgentStatus


class MockSyncSession:
    """Mock synchronous Session for testing."""

    def __init__(self):
        self.commit_called = False

    def commit(self):
        self.commit_called = True

    def close(self):
        pass

    def query(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return []


@pytest.fixture
def mock_db_factory():
    """Factory for mock DB sessions."""
    session = MagicMock()
    session.commit = MagicMock()
    session.close = MagicMock()

    def factory():
        return session

    factory.session = session
    return factory


@pytest.fixture
def risk_agent(mock_db_factory):
    """RiskAgent instance with mock DB."""
    return RiskAgent(mock_db_factory)


class SimpleAgent:
    """Simple agent mock that allows status mutation."""
    def __init__(self, agent_id, name, total_pnl, balance, status=AgentStatus.RUNNING):
        self.id = agent_id
        self.name = name
        self.total_pnl = total_pnl
        self.paper_trading_balance = balance
        self.status = status


def create_agent(agent_id, name, total_pnl, balance, status=AgentStatus.RUNNING):
    """Helper to create a mock Agent."""
    return SimpleAgent(agent_id, name, total_pnl, balance, status)


@pytest.mark.asyncio
async def test_no_breach_broadcasts_portfolio_update(risk_agent, mock_db_factory):
    """Agents with positive PnL → broadcast portfolio_update."""
    agent1 = create_agent(1, "agent1", total_pnl=5000.0, balance=100000.0)
    agent2 = create_agent(2, "agent2", total_pnl=3000.0, balance=100000.0)

    # Mock the query/filter/all chain
    with patch("backend.orchestrator.risk_agent.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        # Mock the session's query method
        mock_db_factory.session.query.return_value.filter.return_value.all.return_value = [agent1, agent2]

        await risk_agent.run()

        # Verify broadcast was called with portfolio_update
        mock_manager.broadcast.assert_called()
        calls = mock_manager.broadcast.call_args_list
        portfolio_update_call = next(
            (c for c in calls if c.args[0].get("event") == "portfolio_update"),
            None
        )
        assert portfolio_update_call is not None
        payload = portfolio_update_call.args[0]
        assert payload["total_pnl"] == 8000.0
        assert payload["total_capital"] == 200000.0
        assert payload["portfolio_drawdown"] == 0.04


@pytest.mark.asyncio
async def test_drawdown_breach_pauses_all(risk_agent, mock_db_factory):
    """Agents with portfolio drawdown -0.30 < -0.25 → all PAUSED."""
    # Single agent with -30k PnL and 100k capital: -30/100 = -0.30 < -0.25 threshold
    agent1 = create_agent(1, "agent1", total_pnl=-30000.0, balance=100000.0)
    agent2 = create_agent(2, "agent2", total_pnl=0.0, balance=0.0)

    with patch("backend.orchestrator.risk_agent.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        # Mock the session's query method
        mock_db_factory.session.query.return_value.filter.return_value.all.return_value = [agent1, agent2]

        # Verify drawdown computation first
        stats = risk_agent._compute_stats([agent1, agent2])
        assert stats["portfolio_drawdown"] == -0.30

        await risk_agent.run()

        # Verify agents were paused
        assert agent1.status == AgentStatus.PAUSED
        assert agent2.status == AgentStatus.PAUSED

        # Verify commit was called
        assert mock_db_factory.session.commit.called

        # Verify broadcasts: bodyguard_pause_all
        calls = mock_manager.broadcast.call_args_list
        bodyguard_calls = [c for c in calls if c.args[0].get("event") == "bodyguard_pause_all"]

        assert len(bodyguard_calls) == 1

        bodyguard_event = bodyguard_calls[0].args[0]
        assert "Portfolio drawdown" in bodyguard_event["reason"]
        assert bodyguard_event["paused_count"] == 2


@pytest.mark.asyncio
async def test_compute_stats():
    """Unit test _compute_stats with mock agent list."""
    risk_agent = RiskAgent(lambda: None)

    agent1 = create_agent(1, "agent1", total_pnl=10000.0, balance=100000.0)
    agent2 = create_agent(2, "agent2", total_pnl=-5000.0, balance=100000.0)
    agent3 = create_agent(3, "agent3", total_pnl=2000.0, balance=100000.0, status=AgentStatus.PAUSED)

    agents = [agent1, agent2, agent3]
    stats = risk_agent._compute_stats(agents)

    assert stats["total_pnl"] == 7000.0
    assert stats["total_capital"] == 300000.0
    assert stats["portfolio_drawdown"] == 7000.0 / 300000.0
    assert stats["agent_count"] == 3
    assert stats["paused_count"] == 1


def test_compute_stats_zero_capital():
    """_compute_stats with zero capital."""
    risk_agent = RiskAgent(lambda: None)

    agent1 = create_agent(1, "agent1", total_pnl=0.0, balance=0.0)

    stats = risk_agent._compute_stats([agent1])

    assert stats["total_pnl"] == 0.0
    assert stats["total_capital"] == 0.0
    assert stats["portfolio_drawdown"] == 0.0
    assert stats["agent_count"] == 1
    assert stats["paused_count"] == 0


@pytest.mark.asyncio
async def test_max_portfolio_drawdown_threshold():
    """RiskAgent.MAX_PORTFOLIO_DRAWDOWN is -0.25."""
    assert RiskAgent.MAX_PORTFOLIO_DRAWDOWN == -0.25


@pytest.mark.asyncio
async def test_bodyguard_pause_all_broadcasts_correct_event():
    """RiskAgent pauses all agents and emits bodyguard_pause_all."""
    # Create agents with drawdown exceeding -0.25: total_pnl / total_capital < -0.25
    # e.g. -35_000 / 100_000 = -0.35 < -0.25
    agent1 = MagicMock(spec=Agent)
    agent1.id = 1
    agent1.name = "A1"
    agent1.status = AgentStatus.IDLE
    agent1.total_pnl = -35_000.0
    agent1.paper_trading_balance = 100_000.0
    agent1.user_id = None  # Mock agents without user_id skip notify

    agent2 = MagicMock(spec=Agent)
    agent2.id = 2
    agent2.name = "A2"
    agent2.status = AgentStatus.IDLE
    agent2.total_pnl = 0.0
    agent2.paper_trading_balance = 0.0
    agent2.user_id = None

    session = MagicMock()
    session.query.return_value.filter.return_value.all.return_value = [agent1, agent2]
    db_factory = MagicMock(return_value=session)

    risk = RiskAgent(db_factory)
    risk.MAX_PORTFOLIO_DRAWDOWN = -0.25

    # Use AsyncMock directly to capture calls
    with patch("backend.orchestrator.risk_agent.manager") as mock_manager:
        mock_manager.broadcast = AsyncMock()

        await risk.run()

        # Verify bodyguard_pause_all event was broadcast
        assert mock_manager.broadcast.called
        calls = mock_manager.broadcast.call_args_list
        bodyguard_calls = [c for c in calls if c.args[0].get("event") == "bodyguard_pause_all"]
        assert len(bodyguard_calls) == 1

    # Verify agents were paused
    assert agent1.status == AgentStatus.PAUSED
    assert agent2.status == AgentStatus.PAUSED


def test_resume_endpoint_resets_confidence_to_50():
    """POST /api/agents/{id}/resume sets confidence_score=50."""
    # This test requires setting up the FastAPI test client with proper DB setup
    # Import inside the function to avoid circular imports
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine, event
    from sqlalchemy.orm import sessionmaker, Session
    from sqlalchemy.pool import StaticPool
    from contextlib import contextmanager
    from backend.main import app
    from backend.database.models import Base, User, UserRole
    from backend.auth.dependencies import get_current_user

    # Setup test DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db_session(database_url):
        @contextmanager
        def session_maker():
            session = SessionLocal()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()

        return session_maker()

    # Patch dependencies
    import backend.api.agents as agents_module

    original_get_db_session = agents_module.get_db_session
    agents_module.get_db_session = override_get_db_session

    # Override auth
    _admin = User(
        id="test-admin",
        username="testadmin",
        email="a@a.com",
        hashed_password="x",
        role=UserRole.ADMIN,
    )
    app.dependency_overrides[get_current_user] = lambda: _admin

    try:
        client = TestClient(app)

        # Create an agent
        payload = {"name": "test_agent", "symbol": "BTC/USD"}
        create_resp = client.post("/api/agents", json=payload)
        assert create_resp.status_code == 201
        agent_id = create_resp.json()["id"]

        # Pause it first
        pause_resp = client.post(f"/api/agents/{agent_id}/pause")
        assert pause_resp.status_code == 200

        # Resume it and verify confidence is reset to 50
        resume_resp = client.post(f"/api/agents/{agent_id}/resume")
        assert resume_resp.status_code == 200
        data = resume_resp.json()
        assert data["confidence_score"] == 50
        assert data["status"] == "idle"
        assert data["consecutive_losses"] == 0
    finally:
        # Restore
        agents_module.get_db_session = original_get_db_session
        app.dependency_overrides.pop(get_current_user, None)
