import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from backend.trading.trade_executor import TradeExecutor
from backend.llm.llm_router import TradeDecision
from backend.database.models import TradeSide, TradeStatus


@pytest.fixture
def mock_vault():
    vault = MagicMock()
    vault.get = MagicMock(return_value="fake_key")
    return vault


@pytest.fixture
def mock_db_session():
    session = MagicMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


@pytest.fixture
def trade_executor(mock_vault, mock_db_session):
    return TradeExecutor(mock_vault, mock_db_session)


def test_calculate_position_size(trade_executor):
    """Position size = min(allocation * LLM_size, hard_cap)."""
    # 100k balance, 10% allocation → 10k available
    # LLM says 5% of 10k → 500
    # cap is 5% of 100k → 5000
    # result should be 500
    result = trade_executor.calculate_position_size(
        agent_capital_allocation=0.1,
        account_balance=100_000.0,
        decision_position_size=0.05,
        max_position_size_percent=0.05,
    )
    assert result == 500.0


def test_position_size_capped(trade_executor):
    """Position size hits hard cap."""
    # 100k balance, 30% allocation → 30k available
    # LLM says 50% of 30k → 15k
    # cap is 5% of 100k → 5000
    # result should be 5000 (capped)
    result = trade_executor.calculate_position_size(
        agent_capital_allocation=0.3,
        account_balance=100_000.0,
        decision_position_size=0.5,
        max_position_size_percent=0.05,
    )
    assert result == 5_000.0


@pytest.mark.asyncio
async def test_execute_hold(trade_executor):
    """HOLD decision returns skipped."""
    decision = TradeDecision(
        action="HOLD", confidence=0.0, position_size=0.0, reasoning="test"
    )
    result = await trade_executor.execute(
        agent_id=1,
        decision=decision,
        agent_config={"broker": "alpaca", "execution_mode": "autonomous"},
        vault=trade_executor.vault,
        db_session=trade_executor.db_session,
    )
    assert result["status"] == "skipped"
    assert result["reason"] == "HOLD decision"


@pytest.mark.asyncio
async def test_execute_human_in_loop(mock_vault, mock_db_session):
    """Human-in-loop execution queues for approval."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector") as mock_get_connector:
        mock_connector = AsyncMock()
        mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)
        mock_get_connector.return_value = mock_connector

        decision = TradeDecision(
            action="BUY", confidence=0.9, position_size=0.1, reasoning="test"
        )

        result = await executor.execute(
            agent_id=1,
            decision=decision,
            agent_config={
                "broker": "alpaca",
                "execution_mode": "human_in_loop",
                "allocation_percent": 0.1,
                "max_position_size": 0.05,
                "asset": "BTC/USD",
            },
            vault=mock_vault,
            db_session=mock_db_session,
        )

        assert result["status"] == "pending_approval"
        assert result["timeout_seconds"] == 30
        assert "trade_id" in result
        assert len(executor.pending_approvals) == 1


@pytest.mark.asyncio
async def test_approve_trade_rejected(mock_vault, mock_db_session):
    """Rejecting a trade removes it from pending_approvals."""
    executor = TradeExecutor(mock_vault, mock_db_session)
    executor.pending_approvals["test_id"] = {
        "agent_id": 1,
        "symbol": "BTC/USD",
        "side": "buy",
    }

    result = await executor.approve_trade("test_id", approved=False)

    assert result["status"] == "rejected"
    assert "test_id" not in executor.pending_approvals


@pytest.mark.asyncio
async def test_execute_live_order(mock_vault, mock_db_session):
    """Live order execution creates Trade record."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector"):
        mock_connector = AsyncMock()
        mock_order = MagicMock()
        mock_order.order_id = "order_123"
        mock_order.filled_price = 50_000.0
        mock_connector.place_order = AsyncMock(return_value=mock_order)

        decision = TradeDecision(
            action="BUY",
            confidence=0.9,
            position_size=0.1,
            stop_loss=-0.05,
            take_profit=0.15,
            reasoning="test",
        )

        result = await executor._execute_live_order(
            agent_id=1,
            symbol="BTC/USD",
            side="buy",
            quantity=1000.0,
            connector=mock_connector,
            db_session=mock_db_session,
            decision=decision,
        )

        assert result["status"] == "executed"
        assert result["order_id"] == "order_123"
        assert result["filled_price"] == 50_000.0
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_execute_autonomous(mock_vault, mock_db_session):
    """Autonomous execution places order immediately."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector") as mock_get_connector:
        mock_connector = AsyncMock()
        mock_connector.get_account_balance = AsyncMock(return_value=100_000.0)
        mock_order = MagicMock()
        mock_order.order_id = "order_456"
        mock_order.filled_price = 50_000.0
        mock_connector.place_order = AsyncMock(return_value=mock_order)
        mock_get_connector.return_value = mock_connector

        decision = TradeDecision(
            action="SELL", confidence=0.85, position_size=0.08, reasoning="test"
        )

        result = await executor.execute(
            agent_id=2,
            decision=decision,
            agent_config={
                "broker": "binance",
                "execution_mode": "autonomous",
                "allocation_percent": 0.2,
                "max_position_size": 0.05,
                "asset": "ETH/USD",
            },
            vault=mock_vault,
            db_session=mock_db_session,
        )

        assert result["status"] == "executed"
        assert result["order_id"] == "order_456"
        mock_connector.place_order.assert_called_once()


@pytest.mark.asyncio
async def test_execute_live_order_calls_notify_when_user_id_set(mock_vault, mock_db_session):
    """Test that notify_trade_executed is called when agent_config has user_id."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector"), patch(
        "backend.notifications.triggers.notify_trade_executed"
    ) as mock_notify_trade:
        mock_connector = AsyncMock()
        mock_order = MagicMock()
        mock_order.order_id = "order_789"
        mock_order.filled_price = 50_000.0
        mock_connector.place_order = AsyncMock(return_value=mock_order)

        decision = TradeDecision(
            action="BUY",
            confidence=0.9,
            position_size=0.1,
            stop_loss=-0.05,
            take_profit=0.15,
            reasoning="test",
        )

        agent_config = {
            "user_id": "user_789",
            "name": "test_agent",
        }

        result = await executor._execute_live_order(
            agent_id=1,
            symbol="BTC/USD",
            side="buy",
            quantity=1000.0,
            connector=mock_connector,
            db_session=mock_db_session,
            decision=decision,
            agent_config=agent_config,
        )

        assert result["status"] == "executed"
        mock_notify_trade.assert_called_once_with(
            user_id="user_789",
            agent_name="test_agent",
            symbol="BTC/USD",
            action="BUY",
            pnl=0.0,
        )


@pytest.mark.asyncio
async def test_execute_live_order_skips_notify_when_no_user_id(mock_vault, mock_db_session):
    """Test that notify_trade_executed is NOT called when agent_config has no user_id."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector"), patch(
        "backend.notifications.triggers.notify_trade_executed"
    ) as mock_notify_trade:
        mock_connector = AsyncMock()
        mock_order = MagicMock()
        mock_order.order_id = "order_999"
        mock_order.filled_price = 50_000.0
        mock_connector.place_order = AsyncMock(return_value=mock_order)

        decision = TradeDecision(
            action="SELL",
            confidence=0.85,
            position_size=0.08,
            reasoning="test",
        )

        agent_config = {
            "name": "test_agent",
        }

        result = await executor._execute_live_order(
            agent_id=2,
            symbol="ETH/USD",
            side="sell",
            quantity=500.0,
            connector=mock_connector,
            db_session=mock_db_session,
            decision=decision,
            agent_config=agent_config,
        )

        assert result["status"] == "executed"
        mock_notify_trade.assert_not_called()


@pytest.mark.asyncio
async def test_execute_live_order_skips_notify_on_exception(mock_vault, mock_db_session):
    """Test that exception in notification doesn't break trade execution."""
    executor = TradeExecutor(mock_vault, mock_db_session)

    with patch("backend.trading.trade_executor.get_connector"), patch(
        "backend.notifications.triggers.notify_trade_executed"
    ) as mock_notify_trade:
        mock_connector = AsyncMock()
        mock_order = MagicMock()
        mock_order.order_id = "order_111"
        mock_order.filled_price = 50_000.0
        mock_connector.place_order = AsyncMock(return_value=mock_order)

        # Mock the notification to raise an exception
        mock_notify_trade.side_effect = Exception("Notification failed")

        decision = TradeDecision(
            action="BUY",
            confidence=0.9,
            position_size=0.1,
            reasoning="test",
        )

        agent_config = {
            "user_id": "user_fail",
            "name": "test_agent",
        }

        result = await executor._execute_live_order(
            agent_id=1,
            symbol="BTC/USD",
            side="buy",
            quantity=1000.0,
            connector=mock_connector,
            db_session=mock_db_session,
            decision=decision,
            agent_config=agent_config,
        )

        # Trade should still execute despite notification failure
        assert result["status"] == "executed"
        mock_notify_trade.assert_called_once()

