"""Kraken connector via krakenex."""

import time
import uuid
from backend.brokers.base import BrokerConnector, MarketData, Order, Position


class KrakenConnector(BrokerConnector):
    """Kraken API connector. ponytail: Kraken has no paper API — simulate paper locally, live uses krakenex."""

    def __init__(self, api_key: str, secret: str, paper: bool = True):
        self._key = api_key
        self._secret = secret
        self._paper = paper
        self._paper_balance = 100_000.0  # ponytail: calibration knob for paper mode

    def _api(self):
        """Return krakenex API instance."""
        import krakenex
        k = krakenex.API()
        k.key = self._key
        k.secret = self._secret
        return k

    async def get_account_balance(self) -> float:
        """Get account balance in USD equivalent."""
        if self._paper:
            return self._paper_balance
        resp = self._api().query_private("Balance")
        if resp.get("error"):
            raise RuntimeError(f"Kraken balance error: {resp['error']}")
        zusd = resp["result"].get("ZUSD", resp["result"].get("USD.F", 0))
        return float(zusd)

    async def get_market_data(self, symbol: str) -> MarketData:
        """Get market data for a symbol."""
        # Kraken symbol format: "BTC/USD" → "XBTUSD" for API
        kraken_sym = symbol.replace("BTC", "XBT").replace("/", "")
        resp = self._api().query_public("Ticker", {"pair": kraken_sym})
        if resp.get("error"):
            raise RuntimeError(f"Kraken ticker error: {resp['error']}")
        data = list(resp["result"].values())[0]
        price = float(data["c"][0])  # last trade closed price
        volume = float(data["v"][1])  # 24h volume
        return MarketData(symbol=symbol, price=price, volume=volume,
                          rsi=None, ma20=None, ma50=None, fetched_at=time.time())

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        """Place an order."""
        if self._paper:
            # ponytail: paper sim — no real order
            return Order(order_id=str(uuid.uuid4()), symbol=symbol, side=side,
                         quantity=quantity, filled_price=None, status="filled")
        kraken_sym = symbol.replace("BTC", "XBT").replace("/", "")
        resp = self._api().query_private("AddOrder", {
            "pair": kraken_sym,
            "type": side.lower(),
            "ordertype": "market",
            "volume": str(quantity),
        })
        if resp.get("error"):
            raise RuntimeError(f"Kraken order error: {resp['error']}")
        txid = resp["result"]["txid"][0]
        return Order(order_id=txid, symbol=symbol, side=side,
                     quantity=quantity, filled_price=None, status="open")

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        """Set stop loss for an order."""
        return False  # ponytail: Kraken stop orders require separate order at creation

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        """Set take profit for an order."""
        return False

    async def get_positions(self) -> list[Position]:
        """Get open positions."""
        if self._paper:
            return []
        resp = self._api().query_private("OpenPositions")
        if resp.get("error"):
            return []
        positions = []
        for pos_id, pos in resp.get("result", {}).items():
            positions.append(Position(
                symbol=pos.get("pair", "UNKNOWN"),
                quantity=float(pos.get("vol", 0)),
                avg_price=float(pos.get("cost", 0)) / max(float(pos.get("vol", 1)), 0.0001),
                unrealized_pnl=float(pos.get("net", 0)),
            ))
        return positions

    async def close_position(self, symbol: str) -> bool:
        """Close a position."""
        positions = await self.get_positions()
        for pos in positions:
            if pos.symbol == symbol.replace("BTC", "XBT").replace("/", ""):
                await self.place_order(symbol, "sell", pos.quantity, "market")
                return True
        return False

    async def test_connection(self) -> bool:
        """Test API connection."""
        try:
            resp = self._api().query_public("ServerTime")
            return not bool(resp.get("error"))
        except Exception:
            return False
