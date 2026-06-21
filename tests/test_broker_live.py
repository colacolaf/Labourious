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


@pytest.mark.asyncio
async def test_alpaca_place_order_polls_for_fill():
    """AlpacaConnector.place_order polls status and returns filled_price when available."""
    from backend.brokers.alpaca import AlpacaConnector
    import httpx

    conn = AlpacaConnector("key", "secret", paper=False)

    order_response = {"id": "order-123", "status": "new"}
    filled_response = {"id": "order-123", "status": "filled", "filled_avg_price": "185.42"}

    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        call_count += 1
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        if "order-123" in url and call_count > 2:
            resp.json = MagicMock(return_value=filled_response)
        else:
            resp.json = MagicMock(return_value=order_response)
        return resp

    async def mock_post(url, **kwargs):
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json = MagicMock(return_value=order_response)
        return resp

    with patch.object(conn, '_client') as mock_client_ctx:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(side_effect=mock_post)
        mock_client.get = AsyncMock(side_effect=mock_get)
        mock_client_ctx.return_value = mock_client

        order = await conn.place_order("AAPL", "buy", 5.0, "market")

    assert order.order_id == "order-123"
    assert order.filled_price == 185.42
