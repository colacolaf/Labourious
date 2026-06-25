import pytest
from unittest.mock import MagicMock, patch, AsyncMock


@pytest.mark.asyncio
async def test_run_agent_backoff_on_repeated_failure():
    """Agent with consecutive_broker_errors >= 1 gets rescheduled with backoff via modify_job."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    session = MagicMock()

    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.name = "TestAgent"
    agent.is_active = True
    agent.status = AgentStatus.IDLE
    agent.consecutive_broker_errors = 3
    agent.broker = "alpaca"
    agent.is_paper_trading = True
    agent.symbol = "AAPL"
    agent.context_file_path = None
    agent.check_frequency = 300
    agent.user_id = None

    session.query.return_value.filter.return_value.first.return_value = agent

    db_factory = MagicMock(return_value=session)
    orchestrator = AgentOrchestrator(vault, db_factory)
    orchestrator.scheduler = MagicMock()

    with patch("backend.orchestrator.agent_orchestrator.get_connector", side_effect=Exception("timeout")):
        await orchestrator.run_agent(1)

    assert session.add.called
    assert agent.consecutive_broker_errors == 4
    orchestrator.scheduler.modify_job.assert_called()


@pytest.mark.asyncio
async def test_circuit_breaker_pauses_agent_at_threshold():
    """Agent auto-pauses when consecutive_broker_errors reaches CIRCUIT_BREAKER_THRESHOLD."""
    from backend.orchestrator.agent_orchestrator import AgentOrchestrator, CIRCUIT_BREAKER_THRESHOLD
    from backend.database.models import Agent, AgentStatus

    vault = MagicMock()
    session = MagicMock()

    agent = MagicMock(spec=Agent)
    agent.id = 2
    agent.name = "CircuitTestAgent"
    agent.is_active = True
    agent.status = AgentStatus.IDLE
    agent.consecutive_broker_errors = CIRCUIT_BREAKER_THRESHOLD - 1
    agent.broker = "alpaca"
    agent.is_paper_trading = True
    agent.symbol = "AAPL"
    agent.context_file_path = None
    agent.check_frequency = 300
    agent.user_id = None

    session.query.return_value.filter.return_value.first.return_value = agent

    db_factory = MagicMock(return_value=session)
    orchestrator = AgentOrchestrator(vault, db_factory)
    orchestrator.scheduler = MagicMock()

    with patch("backend.orchestrator.agent_orchestrator.get_connector", side_effect=Exception("broker down")):
        await orchestrator.run_agent(2)

    assert agent.status == AgentStatus.PAUSED
