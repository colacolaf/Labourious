"""Tests for RiskAgent portfolio monitoring."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.orchestrator.risk_agent import RiskAgent
from backend.database.models import Agent, AgentStatus


class MockAsyncSession:
    """Mock AsyncSession for testing."""

    def __init__(self):
        self.commit_called = False

    async def commit(self):
        self.commit_called = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


@pytest.fixture
def mock_db_factory():
    """Factory for mock DB sessions."""
    session = MockAsyncSession()

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

    # Mock the select/execute chain
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [agent1, agent2]

    with patch("backend.orchestrator.risk_agent.select") as mock_select, \
         patch("backend.orchestrator.risk_agent.manager") as mock_manager:

        mock_select.return_value = MagicMock()
        mock_manager.broadcast = AsyncMock()

        # Mock the session's execute method
        mock_db_factory.session.execute = AsyncMock(return_value=mock_result)

        await risk_agent.run()

        # Verify broadcast was called with portfolio_update
        mock_manager.broadcast.assert_called()
        calls = mock_manager.broadcast.call_args_list
        portfolio_update_call = next(
            (c for c in calls if c[0][0].get("type") == "portfolio_update"),
            None
        )
        assert portfolio_update_call is not None
        payload = portfolio_update_call[0][0]
        assert payload["total_pnl"] == 8000.0
        assert payload["total_capital"] == 200000.0
        assert payload["portfolio_drawdown"] == 0.04


@pytest.mark.asyncio
async def test_drawdown_breach_pauses_all(risk_agent, mock_db_factory):
    """Agents with portfolio drawdown -0.30 < -0.25 → all PAUSED."""
    # Single agent with -30k PnL and 100k capital: -30/100 = -0.30 < -0.25 threshold
    agent1 = create_agent(1, "agent1", total_pnl=-30000.0, balance=100000.0)
    agent2 = create_agent(2, "agent2", total_pnl=0.0, balance=0.0)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [agent1, agent2]

    with patch("backend.orchestrator.risk_agent.select") as mock_select, \
         patch("backend.orchestrator.risk_agent.manager") as mock_manager:

        mock_select.return_value = MagicMock()
        mock_manager.broadcast = AsyncMock()

        mock_db_factory.session.execute = AsyncMock(return_value=mock_result)

        # Verify drawdown computation first
        stats = risk_agent._compute_stats([agent1, agent2])
        assert stats["portfolio_drawdown"] == -0.30

        await risk_agent.run()

        # Verify agents were paused
        assert agent1.status == AgentStatus.PAUSED
        assert agent2.status == AgentStatus.PAUSED

        # Verify commit was called
        assert mock_db_factory.session.commit_called

        # Verify broadcasts: agent_paused x2, then risk_alert
        calls = mock_manager.broadcast.call_args_list
        agent_paused_calls = [c for c in calls if c[0][0].get("type") == "agent_paused"]
        risk_alert_calls = [c for c in calls if c[0][0].get("type") == "risk_alert"]

        assert len(agent_paused_calls) == 2
        assert len(risk_alert_calls) == 1

        risk_alert = risk_alert_calls[0][0][0]
        assert "Portfolio drawdown" in risk_alert["message"]
        assert risk_alert["paused_agents"] == 2


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
