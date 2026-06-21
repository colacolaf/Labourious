import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.brokers.binance import BinanceConnector


@pytest.fixture
def connector():
    with patch("backend.brokers.binance.ccxt.binance") as mock_cls:
        mock_ex = AsyncMock()
        mock_cls.return_value = mock_ex
        conn = BinanceConnector(api_key="k", secret="s")
        conn._exchange = mock_ex
        yield conn


@pytest.mark.asyncio
async def test_get_account_balance(connector):
    connector._exchange.fetch_balance = AsyncMock(return_value={
        "USDT": {"free": 1500.0}, "total": {}
    })
    balance = await connector.get_account_balance()
    assert balance == 1500.0


@pytest.mark.asyncio
async def test_get_market_data(connector):
    connector._exchange.fetch_ticker = AsyncMock(return_value={
        "last": 50000.0, "quoteVolume": 999.0
    })
    md = await connector.get_market_data("BTC/USDT")
    assert md.price == 50000.0
    assert md.symbol == "BTC/USDT"


@pytest.mark.asyncio
async def test_place_order_buy(connector):
    connector._exchange.create_market_buy_order = AsyncMock(return_value={
        "id": "bid-1", "average": 50000.0, "status": "closed"
    })
    order = await connector.place_order("BTC/USDT", "buy", 0.01)
    assert order.order_id == "bid-1"
    assert order.filled_price == 50000.0


@pytest.mark.asyncio
async def test_test_connection_success(connector):
    connector._exchange.fetch_status = AsyncMock(return_value={"status": "ok"})
    assert await connector.test_connection() is True


@pytest.mark.asyncio
async def test_test_connection_failure(connector):
    connector._exchange.fetch_status = AsyncMock(side_effect=Exception("network error"))
    assert await connector.test_connection() is False


def test_manager_returns_correct_connector():
    from backend.brokers.manager import get_connector

    class FakeVault:
        def get(self, key):
            return "fake"

    with patch("backend.brokers.manager.AlpacaConnector") as mock_alpaca:
        get_connector("alpaca", FakeVault())
        mock_alpaca.assert_called_once()

    # Unknown brokers now fallback to generic CCXT connector (Phase 6A.3)
    with patch("backend.brokers.ccxt_generic.CcxtConnector") as mock_ccxt:
        get_connector("unknown_broker", FakeVault())
        mock_ccxt.assert_called_once_with(
            exchange_id="unknown_broker",
            api_key="fake",
            secret="fake",
            paper=True,
        )
