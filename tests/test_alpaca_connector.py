import pytest
import respx
import httpx
from backend.brokers.alpaca import AlpacaConnector, _PAPER_BASE, _DATA_BASE


@pytest.fixture
def connector():
    return AlpacaConnector(api_key="test_key", secret="test_secret", paper=True)


@pytest.mark.asyncio
@respx.mock
async def test_get_account_balance(connector):
    respx.get(f"{_PAPER_BASE}/v2/account").mock(
        return_value=httpx.Response(200, json={"cash": "5000.00"})
    )
    balance = await connector.get_account_balance()
    assert balance == 5000.0


@pytest.mark.asyncio
@respx.mock
async def test_get_market_data(connector):
    respx.get(f"{_DATA_BASE}/v2/stocks/AAPL/snapshot").mock(
        return_value=httpx.Response(200, json={
            "latestTrade": {"p": "175.50"},
            "dailyBar": {"v": "1000000"}
        })
    )
    md = await connector.get_market_data("AAPL")
    assert md.price == 175.50
    assert md.symbol == "AAPL"
    assert md.rsi is None


@pytest.mark.asyncio
@respx.mock
async def test_place_order(connector):
    respx.post(f"{_PAPER_BASE}/v2/orders").mock(
        return_value=httpx.Response(200, json={
            "id": "order-123", "status": "accepted"
        })
    )
    order = await connector.place_order("AAPL", "buy", 1.0)
    assert order.order_id == "order-123"
    assert order.side == "buy"


@pytest.mark.asyncio
@respx.mock
async def test_test_connection_success(connector):
    respx.get(f"{_PAPER_BASE}/v2/account").mock(
        return_value=httpx.Response(200, json={"cash": "1000"})
    )
    assert await connector.test_connection() is True


@pytest.mark.asyncio
async def test_test_connection_failure(connector):
    # no mock → connection error → returns False
    result = await connector.test_connection()
    assert result is False
