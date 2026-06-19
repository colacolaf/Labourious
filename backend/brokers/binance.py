import time
import ccxt.async_support as ccxt
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class BinanceConnector(BrokerConnector):
    def __init__(self, api_key: str, secret: str, paper_balance: float = 100000.0):
        self._exchange = ccxt.binance({
            "apiKey": api_key,
            "secret": secret,
            "enableRateLimit": True,
        })
        # ponytail: Binance has no paper API — simulate locally via paper_balance
        self._paper_balance = paper_balance

    async def get_account_balance(self) -> float:
        balance = await self._exchange.fetch_balance()
        return float(balance.get("USDT", {}).get("free", 0))

    async def get_market_data(self, symbol: str) -> MarketData:
        ticker = await self._exchange.fetch_ticker(symbol)
        return MarketData(
            symbol=symbol,
            price=float(ticker["last"]),
            volume=float(ticker.get("quoteVolume", 0)),
            rsi=None, ma20=None, ma50=None,
            fetched_at=time.time(),
        )

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        method = self._exchange.create_market_buy_order if side.lower() == "buy" \
            else self._exchange.create_market_sell_order
        result = await method(symbol, quantity)
        return Order(
            order_id=str(result["id"]),
            symbol=symbol,
            side=side,
            quantity=quantity,
            filled_price=result.get("average"),
            status=result.get("status", "open"),
        )

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        # ponytail: stop orders require separate OCO — defer to Phase 3
        return False

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        return False

    async def get_positions(self) -> list[Position]:
        balance = await self._exchange.fetch_balance()
        positions = []
        for asset, data in balance.get("total", {}).items():
            if float(data) > 0 and asset != "USDT":
                ticker = await self._exchange.fetch_ticker(f"{asset}/USDT")
                price = float(ticker["last"])
                qty = float(data)
                positions.append(Position(
                    symbol=f"{asset}/USDT",
                    quantity=qty,
                    avg_price=price,
                    unrealized_pnl=0.0,
                ))
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
