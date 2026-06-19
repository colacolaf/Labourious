from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MarketData:
    symbol: str
    price: float
    volume: float
    rsi: float | None
    ma20: float | None
    ma50: float | None
    fetched_at: float  # unix timestamp


@dataclass
class Order:
    order_id: str
    symbol: str
    side: str
    quantity: float
    filled_price: float | None
    status: str


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_price: float
    unrealized_pnl: float


class BrokerConnector(ABC):
    @abstractmethod
    async def get_account_balance(self) -> float: ...

    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData: ...

    @abstractmethod
    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order: ...

    @abstractmethod
    async def set_stop_loss(self, order_id: str, percent: float) -> bool: ...

    @abstractmethod
    async def set_take_profit(self, order_id: str, percent: float) -> bool: ...

    @abstractmethod
    async def get_positions(self) -> list[Position]: ...

    @abstractmethod
    async def close_position(self, symbol: str) -> bool: ...

    @abstractmethod
    async def test_connection(self) -> bool: ...
