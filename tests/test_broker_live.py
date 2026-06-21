import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_connector_alpaca_live_uses_live_base():
    """get_connector with paper=False creates AlpacaConnector pointing to live URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault, paper=False)
    assert "paper-api" not in connector._base
    assert "api.alpaca.markets" in connector._base


def test_get_connector_alpaca_paper_uses_paper_base():
    """get_connector with paper=True (default) creates AlpacaConnector pointing to paper URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault)  # default paper=True
    assert "paper-api.alpaca.markets" in connector._base


def test_get_connector_kraken_returns_kraken_connector():
    """get_connector('kraken') returns a BrokerConnector."""
    from backend.brokers.manager import get_connector
    from backend.brokers.base import BrokerConnector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key"

    connector = get_connector("kraken", vault)
    assert isinstance(connector, BrokerConnector)


@pytest.mark.asyncio
async def test_kraken_connector_test_connection_returns_bool():
    """KrakenConnector.test_connection() returns bool."""
    from backend.brokers.kraken import KrakenConnector
    with patch("krakenex.API.query_public", return_value={"result": {"XXBTZUSD": {}}}):
        conn = KrakenConnector("key", "secret", paper=True)
        result = await conn.test_connection()
        assert isinstance(result, bool)


@pytest.mark.asyncio
async def test_kraken_paper_place_order_returns_order():
    """KrakenConnector paper mode place_order returns Order with uuid."""
    from backend.brokers.kraken import KrakenConnector
    from backend.brokers.base import Order
    conn = KrakenConnector("key", "secret", paper=True)
    conn._paper_balance = 100_000.0
    order = await conn.place_order("BTC/USD", "buy", 500.0, "market")
    assert isinstance(order, Order)
    assert order.order_id is not None


@pytest.mark.asyncio
async def test_ccxt_generic_test_connection_returns_bool():
    """CcxtConnector wraps any ccxt exchange."""
    from backend.brokers.ccxt_generic import CcxtConnector
    conn = CcxtConnector("binance", "key", "secret")
    with patch.object(conn._exchange, "fetch_status", new=AsyncMock(return_value={"status": "ok"})):
        result = await conn.test_connection()
        assert result is True
