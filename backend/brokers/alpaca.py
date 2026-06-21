import time
import asyncio
import httpx
from backend.brokers.base import BrokerConnector, MarketData, Order, Position

_PAPER_BASE = "https://paper-api.alpaca.markets"
_LIVE_BASE = "https://api.alpaca.markets"
_DATA_BASE = "https://data.alpaca.markets"


class AlpacaConnector(BrokerConnector):
    def __init__(self, api_key: str, secret: str, paper: bool = True):
        self._key = api_key
        self._secret = secret
        self._base = _PAPER_BASE if paper else _LIVE_BASE
        self._headers = {"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": secret}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self._headers, timeout=30.0)

    async def get_account_balance(self) -> float:
        async with self._client() as c:
            r = await c.get(f"{self._base}/v2/account")
            r.raise_for_status()
            return float(r.json()["cash"])

    async def get_market_data(self, symbol: str) -> MarketData:
        # ponytail: snapshot endpoint, no indicators — add pandas-ta calc if needed
        async with self._client() as c:
            r = await c.get(f"{_DATA_BASE}/v2/stocks/{symbol}/snapshot")
            r.raise_for_status()
            snap = r.json()
        price = float(snap["latestTrade"]["p"])
        volume = float(snap.get("dailyBar", {}).get("v", 0))
        return MarketData(symbol=symbol, price=price, volume=volume,
                          rsi=None, ma20=None, ma50=None, fetched_at=time.time())

    async def place_order(self, symbol: str, side: str, quantity: float,
                          order_type: str = "market") -> Order:
        payload = {"symbol": symbol, "qty": quantity, "side": side,
                   "type": order_type, "time_in_force": "gtc"}
        async with self._client() as c:
            r = await c.post(f"{self._base}/v2/orders", json=payload)
            r.raise_for_status()
            o = r.json()

        order_id = o["id"]
        filled_price = None

        # Poll up to 5s for fill confirmation (market orders usually fill in <1s)
        for _ in range(5):
            await asyncio.sleep(1)
            async with self._client() as c:
                r = await c.get(f"{self._base}/v2/orders/{order_id}")
                r.raise_for_status()
                status_data = r.json()
            if status_data.get("status") in ("filled", "partially_filled"):
                filled_price = float(status_data["filled_avg_price"]) if status_data.get("filled_avg_price") else None
                break

        return Order(order_id=order_id, symbol=symbol, side=side,
                     quantity=quantity, filled_price=filled_price, status=o["status"])

    async def set_stop_loss(self, order_id: str, percent: float) -> bool:
        # ponytail: bracket orders need order_id at create-time; patching after unsupported on Alpaca
        return False

    async def set_take_profit(self, order_id: str, percent: float) -> bool:
        return False

    async def get_positions(self) -> list[Position]:
        async with self._client() as c:
            r = await c.get(f"{self._base}/v2/positions")
            r.raise_for_status()
        return [
            Position(symbol=p["symbol"], quantity=float(p["qty"]),
                     avg_price=float(p["avg_entry_price"]),
                     unrealized_pnl=float(p["unrealized_pl"]))
            for p in r.json()
        ]

    async def close_position(self, symbol: str) -> bool:
        async with self._client() as c:
            r = await c.delete(f"{self._base}/v2/positions/{symbol}")
            return r.status_code == 200

    async def test_connection(self) -> bool:
        try:
            async with self._client() as c:
                r = await c.get(f"{self._base}/v2/account")
                return r.status_code == 200
        except Exception:
            return False
