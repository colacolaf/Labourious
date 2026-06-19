import pytest
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


def test_dataclasses_instantiate():
    md = MarketData(symbol="BTC/USD", price=50000.0, volume=1000.0,
                    rsi=55.0, ma20=49000.0, ma50=48000.0, fetched_at=1234567890.0)
    assert md.price == 50000.0

    order = Order(order_id="123", symbol="BTC/USD", side="buy",
                  quantity=0.1, filled_price=50001.0, status="filled")
    assert order.side == "buy"

    pos = Position(symbol="BTC/USD", quantity=0.1, avg_price=50000.0, unrealized_pnl=100.0)
    assert pos.unrealized_pnl == 100.0


def test_abc_cannot_instantiate():
    with pytest.raises(TypeError):
        BrokerConnector()
