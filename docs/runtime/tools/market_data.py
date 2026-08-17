# tools/market_data.py — Market data layer. Free: yfinance (no key) + FRED (key, free).
from __future__ import annotations
import os
import time
from dataclasses import dataclass, field
from typing import Any
from . import ToolResult


@dataclass
class MarketDataTool:
    """
    Default: yfinance for prices, FRED for macro series.
    FRED requires a free API key (https://fred.stlouisfed.org/docs/api/api_key.html).
    yfinance works keyless.
    """
    fred_api_key: str | None = None

    def __post_init__(self):
        self.fred_api_key = self.fred_api_key or os.environ.get("FRED_API_KEY")

    def price_history(self, ticker: str, period: str = "1y",
                      interval: str = "1d") -> ToolResult:
        """OHLCV via yfinance. Returns a ToolResult with records as a list of dicts."""
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        try:
            import yfinance as yf  # type: ignore
        except ImportError:
            return ToolResult(
                status="FAILED", data=None, as_of=as_of, source="yfinance",
                note="yfinance not installed; pip install yfinance.",
            )
        try:
            t = yf.Ticker(ticker)
            df = t.history(period=period, interval=interval)
            if df.empty:
                return ToolResult(status="EMPTY", data=[], as_of=as_of,
                                  source="yfinance", note=f"no data for {ticker} {period}/{interval}")
            records = []
            for idx, row in df.iterrows():
                records.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "Open": float(row["Open"]),
                    "High": float(row["High"]),
                    "Low": float(row["Low"]),
                    "Close": float(row["Close"]),
                    "Volume": int(row["Volume"]),
                })
            return ToolResult(status="SUCCESS", data=records, as_of=as_of,
                              source="yfinance", note=f"{ticker} {period}/{interval}: {len(records)} rows")
        except Exception as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of,
                              source="yfinance", note=f"yfinance error: {e}")

    def fred_series(self, series_id: str, limit: int = 100) -> ToolResult:
        """Macro series via FRED. Requires FRED_API_KEY."""
        as_of = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        if not self.fred_api_key:
            return ToolResult(status="FAILED", data=None, as_of=as_of,
                              source="fred", note="FRED_API_KEY not set")
        try:
            import urllib.request, json
            url = (f"https://api.stlouisfed.org/fred/series/observations"
                   f"?series_id={series_id}&api_key={self.fred_api_key}"
                   f"&file_type=json&sort_order=desc&limit={limit}")
            with urllib.request.urlopen(url, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
            obs = payload.get("observations", [])
            return ToolResult(status="SUCCESS" if obs else "EMPTY",
                              data=obs, as_of=as_of, source="fred",
                              note=f"FRED {series_id}: {len(obs)} observations")
        except Exception as e:
            return ToolResult(status="FAILED", data=None, as_of=as_of,
                              source="fred", note=f"fred error: {e}")
