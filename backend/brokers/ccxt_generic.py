"""Generic CCXT connector stub for Phase 6A.3."""

from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class CcxtConnector(BrokerConnector):
    """Generic CCXT-based connector for exchanges. Stub for Phase 6A.3."""

    def __init__(self, exchange_id: str, api_key: str, secret: str):
        self._exchange_id = exchange_id
        self._key = api_key
        self._secret = secret

    async def get_account_balance(self) -> float:
        raise NotImplementedError("Phase 6A.3")

    async def get_market_data(self, symbol: str) -> MarketData:
        raise NotImplementedError("Phase 6A.3")

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        raise NotImplementedError("Phase 6A.3")

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        raise NotImplementedError("Phase 6A.3")

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        raise NotImplementedError("Phase 6A.3")

    async def get_positions(self) -> list[Position]:
        raise NotImplementedError("Phase 6A.3")

    async def close_position(self, symbol: str) -> bool:
        raise NotImplementedError("Phase 6A.3")

    async def test_connection(self) -> bool:
        raise NotImplementedError("Phase 6A.3")
