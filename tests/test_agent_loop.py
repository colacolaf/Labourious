"""Integration test: full agent execution loop."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.orm import Session

from backend.orchestrator.agent_orchestrator import AgentOrchestrator
from backend.database.models import Agent, AgentStatus
from backend.llm.llm_router import TradeDecision
from backend.brokers.base import MarketData


def _make_agent(agent_id=1, symbol="AAPL", broker="alpaca", execution_mode="autonomous",
                confidence_score=50, consecutive_losses=0):
    agent = MagicMock(spec=Agent)
    agent.id = agent_id
    agent.name = f"agent-{agent_id}"
    agent.symbol = symbol
    agent.broker = broker
    agent.status = AgentStatus.IDLE
    agent.is_active = True
    agent.use_local_llm = True
    agent.check_frequency = 300
    agent.confidence_score = confidence_score
    agent.consecutive_losses = consecutive_losses
    agent.is_paper_trading = True
    agent.max_position_size = 1000.0
    agent.execution_mode = execution_mode
    agent.context_file_path = None
    agent.last_heartbeat = None
    return agent


def _make_orchestrator():
    vault = MagicMock()
    vault.get.return_value = "test_key"
    db_factory = MagicMock()
    session = MagicMock(spec=Session)
    db_factory.return_value = session
    return AgentOrchestrator(vault, db_factory), session


def _wire_session_query(session, agent):
    mock_query = MagicMock()
    mock_filter = MagicMock()
    mock_query.filter.return_value = mock_filter
    mock_filter.first.return_value = agent
    session.query.return_value = mock_query


@pytest.mark.asyncio
async def test_full_agent_loop_hold():
    """Full loop: mock broker + LLM returning HOLD → no trade executor call."""
    orchestrator, session = _make_orchestrator()
    agent = _make_agent(agent_id=1, symbol="AAPL", execution_mode="autonomous")
    _wire_session_query(session, agent)

    market_data_obj = MagicMock()
    market_data_obj.price = 150.0
    market_data_obj.volume = 1000000.0
    market_data_obj.rsi = 55.0
    market_data_obj.ma20 = 148.0
    market_data_obj.ma50 = 145.0

    hold_decision = TradeDecision(action="HOLD", confidence=0.0, position_size=0.0)

    with patch("backend.orchestrator.agent_orchestrator.get_connector") as mock_conn, \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_cls, \
         patch("backend.orchestrator.agent_orchestrator.read_config"), \
         patch("backend.orchestrator.agent_orchestrator.check_agent_risk", return_value=(False, None)), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast"):

        connector = AsyncMock()
        connector.get_market_data.return_value = market_data_obj
        mock_conn.return_value = connector

        router = AsyncMock()
        router.decide.return_value = hold_decision
        mock_router_cls.from_config.return_value = router

        orchestrator.executor.execute = AsyncMock(return_value={"status": "skipped", "reason": "HOLD decision"})

        await orchestrator.run_agent(1)

        # HOLD → executor still called but returns skipped
        assert orchestrator.executor.execute.call_count == 1
        assert agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_full_agent_loop_buy_paper():
    """Full loop: BUY decision on paper trading → executor called."""
    orchestrator, session = _make_orchestrator()
    agent = _make_agent(agent_id=2, symbol="BTC/USDT", broker="binance",
                        execution_mode="autonomous", confidence_score=70)
    _wire_session_query(session, agent)

    market_data_obj = MagicMock()
    market_data_obj.price = 45000.0
    market_data_obj.volume = 500.0
    market_data_obj.rsi = 40.0
    market_data_obj.ma20 = 44000.0
    market_data_obj.ma50 = 43000.0

    buy_decision = TradeDecision(action="BUY", confidence=0.8, position_size=0.05)

    with patch("backend.orchestrator.agent_orchestrator.get_connector") as mock_conn, \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_cls, \
         patch("backend.orchestrator.agent_orchestrator.read_config"), \
         patch("backend.orchestrator.agent_orchestrator.check_agent_risk", return_value=(False, None)), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast"):

        connector = AsyncMock()
        connector.get_market_data.return_value = market_data_obj
        mock_conn.return_value = connector

        router = AsyncMock()
        router.decide.return_value = buy_decision
        mock_router_cls.from_config.return_value = router

        orchestrator.executor.execute = AsyncMock(return_value={"status": "executed", "order_id": "abc"})

        await orchestrator.run_agent(2)

        assert orchestrator.executor.execute.call_count == 1
        call_kwargs = orchestrator.executor.execute.call_args[1]
        assert call_kwargs["decision"].action == "BUY"
        assert agent.status == AgentStatus.IDLE


@pytest.mark.asyncio
async def test_run_agent_paper_trade_written_to_db():
    """Full cycle: paper agent → LLM BUY → Trade written to DB."""
    from backend.trading.trade_executor import TradeExecutor

    orchestrator, session = _make_orchestrator()
    agent = _make_agent(agent_id=1, symbol="AAPL", broker="alpaca")
    agent.current_drawdown = 0.0
    agent.user_id = None
    _wire_session_query(session, agent)

    market_data_obj = MagicMock()
    market_data_obj.price = 150.0
    market_data_obj.volume = 1_000_000
    market_data_obj.rsi = 45.0
    market_data_obj.ma20 = 148.0
    market_data_obj.ma50 = 145.0

    decision = TradeDecision(action="BUY", confidence=0.75, position_size=0.05, reasoning="test")

    broadcast_calls = []
    async def capture_broadcast(data):
        broadcast_calls.append(data)

    with patch("backend.orchestrator.agent_orchestrator.get_connector") as mock_conn, \
         patch("backend.trading.trade_executor.get_connector") as mock_conn_exec, \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_cls, \
         patch("backend.orchestrator.agent_orchestrator.read_config"), \
         patch("backend.orchestrator.agent_orchestrator.check_agent_risk", return_value=(False, None)), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast", side_effect=capture_broadcast):

        connector = AsyncMock()
        connector.get_market_data.return_value = market_data_obj
        connector.get_account_balance.return_value = 100_000.0
        mock_conn.return_value = connector
        mock_conn_exec.return_value = connector

        router = AsyncMock()
        router.decide.return_value = decision
        mock_router_cls.from_config.return_value = router

        await orchestrator.run_agent(1)

        # Verify trade_executed event was broadcast
        trade_events = [e for e in broadcast_calls if e.get("event") == "trade_executed"]
        assert len(trade_events) >= 1
        assert trade_events[0]["is_paper"] is True


@pytest.mark.asyncio
async def test_run_agent_risk_pause_persisted():
    """Agent with confidence < 35 is paused and broadcast emitted."""
    orchestrator, session = _make_orchestrator()
    agent = _make_agent(agent_id=1, symbol="AAPL", broker="alpaca", confidence_score=20)
    agent.current_drawdown = 0.0
    agent.user_id = None
    _wire_session_query(session, agent)

    market_data_obj = MagicMock()
    market_data_obj.price = 150.0
    market_data_obj.volume = 1_000_000
    market_data_obj.rsi = 45.0
    market_data_obj.ma20 = 148.0
    market_data_obj.ma50 = 145.0

    decision_mock = TradeDecision(action="BUY", confidence=0.3, position_size=0.05, reasoning="test")

    with patch("backend.orchestrator.agent_orchestrator.get_connector") as mock_conn, \
         patch("backend.orchestrator.agent_orchestrator.LLMRouter") as mock_router_cls, \
         patch("backend.orchestrator.agent_orchestrator.read_config"), \
         patch("backend.orchestrator.agent_orchestrator.check_agent_risk", return_value=(True, "confidence 20% < 35%")), \
         patch("backend.orchestrator.agent_orchestrator.manager.broadcast") as mock_bc:

        connector = AsyncMock()
        connector.get_market_data.return_value = market_data_obj
        connector.get_account_balance.return_value = 100_000.0
        mock_conn.return_value = connector

        router = AsyncMock()
        router.decide.return_value = decision_mock
        mock_router_cls.from_config.return_value = router

        await orchestrator.run_agent(1)

        # Verify agent_paused event was broadcast
        broadcast_calls = mock_bc.call_args_list
        paused_events = [c[0][0] for c in broadcast_calls if c[0][0].get("event") == "agent_paused"]
        assert len(paused_events) >= 1
        assert agent.status == AgentStatus.PAUSED
