"""Generic CCXT connector for any ccxt-compatible exchange."""

import uuid
import time
import ccxt.async_support as ccxt
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class CcxtConnector(BrokerConnector):
    """Generic ccxt connector — supports any ccxt-compatible exchange."""

    def __init__(self, exchange_id: str, api_key: str, secret: str, paper: bool = True):
        if not hasattr(ccxt, exchange_id):
            raise ValueError(f"Unknown ccxt exchange: {exchange_id}")
        self._paper = paper
        self._paper_balance = 100_000.0  # ponytail: calibration knob for paper mode
        self._exchange = getattr(ccxt, exchange_id)({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })

    async def get_account_balance(self) -> float:
        if self._paper:
            return self._paper_balance
        balance = await self._exchange.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0))

    async def get_market_data(self, symbol: str) -> MarketData:
        ticker = await self._exchange.fetch_ticker(symbol)
        return MarketData(symbol=symbol, price=float(ticker["last"]),
                          volume=float(ticker.get("quoteVolume", 0)),
                          rsi=None, ma20=None, ma50=None, fetched_at=time.time())

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        if self._paper:
            # ponytail: paper sim — no real order
            return Order(order_id=str(uuid.uuid4()), symbol=symbol, side=side,
                         quantity=quantity, filled_price=None, status="filled")
        method = (self._exchange.create_market_buy_order if side.lower() == "buy"
                  else self._exchange.create_market_sell_order)
        result = await method(symbol, quantity)
        return Order(order_id=str(result["id"]), symbol=symbol, side=side,
                     quantity=quantity, filled_price=result.get("average"),
                     status=result.get("status", "open"))

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        return False  # ponytail: exchange-specific; implement per-exchange if needed

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        return False

    async def get_positions(self) -> list[Position]:
        balance = await self._exchange.fetch_balance()
        positions = []
        for asset, data in balance.get("total", {}).items():
            qty = float(data) if data else 0.0
            if qty > 0 and asset != "USDT":
                try:
                    ticker = await self._exchange.fetch_ticker(f"{asset}/USDT")
                    positions.append(Position(symbol=f"{asset}/USDT", quantity=qty,
                                              avg_price=float(ticker["last"]), unrealized_pnl=0.0))
                except (ccxt.NetworkError, ccxt.ExchangeError):
                    # Skip position if ticker fetch fails (network or exchange issue)
                    pass
        return positions

    async def close_position(self, symbol: str) -> bool:
        balance = await self._exchange.fetch_balance()
        asset = symbol.split("/")[0]
        qty = float(balance.get("free", {}).get(asset, 0))
        if qty <= 0:
            return False
        await self._exchange.create_market_sell_order(symbol, qty)
        return True

    async def test_connection(self) -> bool:
        try:
            await self._exchange.fetch_status()
            return True
        except Exception:
            return False

    async def close(self):
        await self._exchange.close()
