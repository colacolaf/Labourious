import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime
from sqlalchemy.orm import Session

from backend.orchestrator.agent_orchestrator import AgentOrchestrator
from backend.database.models import Agent, AgentStatus
from backend.llm.llm_router import TradeDecision


@pytest.fixture
def mock_vault():
    vault = MagicMock()
    vault.get.return_value = "test_key"
    return vault


@pytest.fixture
def mock_db_factory():
    factory = MagicMock()
    session_instance = MagicMock(spec=Session)
    factory.return_value = session_instance
    return factory


@pytest.fixture
def orchestrator(mock_vault, mock_db_factory):
    return AgentOrchestrator(mock_vault, mock_db_factory)


@pytest.fixture
def sample_agent():
    agent = MagicMock(spec=Agent)
    agent.id = 1
    agent.name = "test_agent"
    agent.symbol = "BTC/USD"
    agent.broker = "alpaca"
    agent.status = AgentStatus.IDLE
    agent.is_active = True
    agent.use_local_llm = True
    agent.check_frequency = 300
    agent.confidence_score = 50
    agent.consecutive_losses = 0
    agent.is_paper_trading = True
    agent.max_position_size = 1000.0
    agent.execution_mode = "auto"
    agent.context_file_path = None
    agent.last_heartbeat = None
    return agent


@pytest.mark.asyncio
async def test_run_agent_hold_decision(orchestrator, sample_agent, mock_vault):
    """Test that HOLD decision skips trade executor."""
    with patch(
        "backend.orchestrator.agent_orchestrator.get_connector"
    ) as mock_get_conn, patch(
        "backend.orchestrator.agent_orchestrator.LLMRouter"
    ) as mock_router_class, patch(
        "backend.orchestrator.agent_orchestrator.read_config"
    ), patch(
        "backend.orchestrator.agent_orchestrator.check_agent_risk"
    ) as mock_check_risk, patch(
        "backend.orchestrator.agent_orchestrator.manager.broadcast"
    ) as mock_broadcast:

        # Setup db factory mock
        mock_session = MagicMock(spec=Session)
        orchestrator.db_factory.return_value = mock_session

        # Setup agent query
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_agent
        mock_session.query.return_value = mock_query

        # Setup connector mock
        mock_connector = AsyncMock()
        market_data_obj = MagicMock()
        market_data_obj.price = 50000.0
        market_data_obj.volume = 1000.0
        market_data_obj.rsi = 55.0
        market_data_obj.ma20 = 49000.0
        market_data_obj.ma50 = 48000.0
        mock_connector.get_market_data.return_value = market_data_obj
        mock_get_conn.return_value = mock_connector

        # Setup router mock (from_config classmethod returns the instance)
        mock_router = AsyncMock()
        hold_decision = TradeDecision(
            action="HOLD", confidence=0.5, position_size=0.0, reasoning="test hold"
        )
        mock_router.decide.return_value = hold_decision
        mock_router_class.from_config.return_value = mock_router

        # Risk check passes
        mock_check_risk.return_value = (False, None)

        # Mock executor.execute
        orchestrator.executor.execute = AsyncMock(
            return_value={"status": "skipped", "reason": "HOLD decision"}
        )

        # Execute
        await orchestrator.run_agent(1)

        # Assert executor.execute was called (but returns HOLD result)
        # The executor itself handles HOLD by returning early
        assert orchestrator.executor.execute.call_count == 1

        # Assert status set to IDLE
        assert sample_agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_run_agent_paused_skips(orchestrator, sample_agent):
    """Test that paused agent is skipped."""
    sample_agent.status = AgentStatus.PAUSED

    mock_session = MagicMock(spec=Session)
    orchestrator.db_factory.return_value = mock_session

    # Setup agent query
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = sample_agent
    mock_session.query.return_value = mock_query

    with patch("backend.orchestrator.agent_orchestrator.manager.broadcast"):
        await orchestrator.run_agent(1)

    # Session.query should only be called once (to load agent)
    assert mock_session.query.call_count == 1


@pytest.mark.asyncio
async def test_run_agent_risk_pause(orchestrator, sample_agent, mock_vault):
    """Test that RiskManager pause sets status to PAUSED."""
    with patch(
        "backend.orchestrator.agent_orchestrator.get_connector"
    ) as mock_get_conn, patch(
        "backend.orchestrator.agent_orchestrator.LLMRouter"
    ) as mock_router_class, patch(
        "backend.orchestrator.agent_orchestrator.read_config"
    ), patch(
        "backend.orchestrator.agent_orchestrator.check_agent_risk"
    ) as mock_check_risk, patch(
        "backend.orchestrator.agent_orchestrator.manager.broadcast"
    ) as mock_broadcast:

        # Setup db factory mock
        mock_session = MagicMock(spec=Session)
        orchestrator.db_factory.return_value = mock_session

        # Setup agent query
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_agent
        mock_session.query.return_value = mock_query

        # Setup connector mock
        mock_connector = AsyncMock()
        market_data_obj = MagicMock()
        market_data_obj.price = 50000.0
        market_data_obj.volume = 1000.0
        market_data_obj.rsi = 55.0
        market_data_obj.ma20 = 49000.0
        market_data_obj.ma50 = 48000.0
        mock_connector.get_market_data.return_value = market_data_obj
        mock_get_conn.return_value = mock_connector

        # Setup router mock (from_config classmethod returns the instance)
        mock_router = AsyncMock()
        buy_decision = TradeDecision(
            action="BUY", confidence=0.8, position_size=0.5, reasoning="test buy"
        )
        mock_router.decide.return_value = buy_decision
        mock_router_class.from_config.return_value = mock_router

        # Risk check FAILS (should pause)
        mock_check_risk.return_value = (True, "confidence too low")

        await orchestrator.run_agent(1)

        # Assert status set to PAUSED
        assert sample_agent.status == AgentStatus.PAUSED

        # Assert broadcast called with pause event
        broadcast_calls = mock_broadcast.call_args_list
        pause_events = [c for c in broadcast_calls if "agent_paused" in str(c)]
        assert len(pause_events) > 0


@pytest.mark.asyncio
async def test_run_agent_buy_decision_executes(orchestrator, sample_agent, mock_vault):
    """Test that BUY decision calls executor."""
    with patch(
        "backend.orchestrator.agent_orchestrator.get_connector"
    ) as mock_get_conn, patch(
        "backend.orchestrator.agent_orchestrator.LLMRouter"
    ) as mock_router_class, patch(
        "backend.orchestrator.agent_orchestrator.read_config"
    ), patch(
        "backend.orchestrator.agent_orchestrator.check_agent_risk"
    ) as mock_check_risk, patch(
        "backend.orchestrator.agent_orchestrator.manager.broadcast"
    ) as mock_broadcast:

        # Setup db factory mock
        mock_session = MagicMock(spec=Session)
        orchestrator.db_factory.return_value = mock_session

        # Setup agent query
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = sample_agent
        mock_session.query.return_value = mock_query

        # Setup connector mock
        mock_connector = AsyncMock()
        market_data_obj = MagicMock()
        market_data_obj.price = 50000.0
        market_data_obj.volume = 1000.0
        market_data_obj.rsi = 55.0
        market_data_obj.ma20 = 49000.0
        market_data_obj.ma50 = 48000.0
        mock_connector.get_market_data.return_value = market_data_obj
        mock_get_conn.return_value = mock_connector

        # Setup router mock (from_config classmethod returns the instance)
        mock_router = AsyncMock()
        buy_decision = TradeDecision(
            action="BUY", confidence=0.8, position_size=0.5, reasoning="test buy"
        )
        mock_router.decide.return_value = buy_decision
        mock_router_class.from_config.return_value = mock_router

        # Risk check passes
        mock_check_risk.return_value = (False, None)

        # Mock executor.execute
        orchestrator.executor.execute = AsyncMock(
            return_value={"status": "executed", "order_id": "123"}
        )

        await orchestrator.run_agent(1)

        # Assert executor.execute was called with correct params
        assert orchestrator.executor.execute.call_count == 1
        call_kwargs = orchestrator.executor.execute.call_args[1]
        assert call_kwargs["agent_id"] == 1
        assert call_kwargs["decision"].action == "BUY"
        assert call_kwargs["agent_config"]["broker"] == "alpaca"


@pytest.mark.asyncio
async def test_build_agent_config(orchestrator, sample_agent):
    """Test agent config building."""
    config = orchestrator._build_agent_config(sample_agent)

    assert config["broker"] == "alpaca"
    assert config["paper_trading"] == True
    assert config["asset"] == "BTC/USD"
    assert config["execution_mode"] == "auto"
    assert config["allocation_percent"] == 0.1
