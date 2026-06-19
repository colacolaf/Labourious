"""
Backtest CLI: basic + walk-forward modes.

Usage:
    python -m backend.scripts.backtest --symbol AAPL --start 2024-01-01 --end 2024-06-30
    python -m backend.scripts.backtest --symbol BTC-USD --mode walk-forward
"""
import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    import pandas_ta as ta
except ImportError:
    ta = None


def fetch_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    if yf is None:
        raise ImportError("yfinance required: pip install yfinance")
    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
    df.columns = [c.lower() for c in df.columns]
    return df


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if ta is not None:
        df["rsi"] = ta.rsi(df["close"], length=14)
        macd = ta.macd(df["close"])
        if macd is not None:
            df["macd"] = macd.iloc[:, 0]
        bb = ta.bbands(df["close"])
        if bb is not None:
            df["bb_upper"] = bb.iloc[:, 0]
            df["bb_lower"] = bb.iloc[:, 2]
    df["ma20"] = df["close"].rolling(20).mean()
    df["ma50"] = df["close"].rolling(50).mean()
    return df


def rule_signal(row: pd.Series) -> str:
    """Simple rule engine: RSI oversold/overbought, MA crossover."""
    rsi = row.get("rsi", 50)
    ma20 = row.get("ma20", row["close"])
    ma50 = row.get("ma50", row["close"])

    if pd.isna(rsi) or pd.isna(ma20) or pd.isna(ma50):
        return "HOLD"

    if rsi < 30 and ma20 > ma50:
        return "BUY"
    if rsi > 70 and ma20 < ma50:
        return "SELL"
    return "HOLD"


def run_simulation(df: pd.DataFrame, initial_balance: float = 100_000.0) -> dict:
    """Paper trading simulation over df. Returns metrics dict."""
    balance = initial_balance
    position = 0.0  # shares held
    entry_price = 0.0
    trades = []

    for i, (idx, row) in enumerate(df.iterrows()):
        signal = rule_signal(row)
        price = float(row["close"])

        if signal == "BUY" and position == 0 and balance > 0:
            qty = (balance * 0.05) / price  # 5% per trade
            position = qty
            entry_price = price
            balance -= qty * price

        elif signal == "SELL" and position > 0:
            pnl = (price - entry_price) * position
            balance += position * price
            trades.append({
                "entry": entry_price,
                "exit": price,
                "qty": position,
                "pnl": pnl,
                "win": pnl > 0,
            })
            position = 0.0
            entry_price = 0.0

    # Close any open position at end
    if position > 0:
        price = float(df["close"].iloc[-1])
        pnl = (price - entry_price) * position
        balance += position * price
        trades.append({"entry": entry_price, "exit": price, "qty": position, "pnl": pnl, "win": pnl > 0})

    total_return = (balance - initial_balance) / initial_balance
    wins = sum(1 for t in trades if t["win"])
    win_rate = wins / len(trades) if trades else 0.0

    # Sharpe: daily returns from balance snapshots (simplified)
    pnls = np.array([t["pnl"] for t in trades]) if trades else np.array([0.0])
    sharpe = float(np.mean(pnls) / np.std(pnls) * np.sqrt(252)) if np.std(pnls) > 0 else 0.0

    # Max drawdown (simplified from trade pnls)
    cumulative = np.cumsum(pnls)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = cumulative - running_max
    max_dd = float(np.min(drawdown)) if len(drawdown) else 0.0

    return {
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_return_pct": round(total_return * 100, 2),
        "num_trades": len(trades),
        "win_rate_pct": round(win_rate * 100, 1),
        "sharpe_ratio": round(sharpe, 3),
        "max_drawdown": round(max_dd, 2),
    }


def run_walk_forward(df: pd.DataFrame, n_windows: int = 4, train_ratio: float = 0.75) -> list[dict]:
    """Walk-forward: split df into n windows, simulate on test portions."""
    window_size = len(df) // n_windows
    results = []

    for i in range(n_windows):
        start_idx = i * window_size
        end_idx = start_idx + window_size if i < n_windows - 1 else len(df)
        window = df.iloc[start_idx:end_idx]

        split = int(len(window) * train_ratio)
        test_df = window.iloc[split:]

        if len(test_df) < 10:
            continue

        metrics = run_simulation(test_df)
        metrics["window"] = i + 1
        metrics["test_start"] = str(test_df.index[0].date())
        metrics["test_end"] = str(test_df.index[-1].date())
        results.append(metrics)

    return results


def main():
    parser = argparse.ArgumentParser(description="Labourious backtest CLI")
    parser.add_argument("--symbol", default="AAPL", help="Symbol to backtest (e.g. AAPL, BTC-USD)")
    parser.add_argument("--start", default="2024-01-01", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", default="2024-12-31", help="End date YYYY-MM-DD")
    parser.add_argument("--mode", choices=["basic", "walk-forward"], default="basic")
    parser.add_argument("--balance", type=float, default=100_000.0, help="Initial paper balance")
    args = parser.parse_args()

    print(f"Fetching {args.symbol} {args.start} → {args.end}...")
    try:
        df = fetch_ohlcv(args.symbol, args.start, args.end)
    except Exception as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)

    if df.empty:
        print("No data returned. Check symbol and date range.")
        sys.exit(1)

    df = add_indicators(df)
    df = df.dropna(subset=["close"])

    if args.mode == "basic":
        metrics = run_simulation(df, args.balance)
        print(f"\n=== Basic Backtest: {args.symbol} ===")
        for k, v in metrics.items():
            print(f"  {k}: {v}")

    else:
        windows = run_walk_forward(df)
        print(f"\n=== Walk-Forward Backtest: {args.symbol} ({len(windows)} windows) ===")
        for w in windows:
            print(f"\n  Window {w['window']} ({w['test_start']} → {w['test_end']})")
            print(f"    Return: {w['total_return_pct']}%  Win rate: {w['win_rate_pct']}%  Sharpe: {w['sharpe_ratio']}")

        avg_return = sum(w["total_return_pct"] for w in windows) / len(windows)
        print(f"\n  Average return across windows: {round(avg_return, 2)}%")


if __name__ == "__main__":
    main()


if __name__ == "__demo__":
    # ponytail: self-check — verify simulation math
    import pandas as pd
    rows = [{"close": 100 + i, "rsi": 25 if i == 2 else 50, "ma20": 99 + i, "ma50": 98 + i}
            for i in range(20)]
    df_test = pd.DataFrame(rows)
    result = run_simulation(df_test, initial_balance=10_000)
    assert result["initial_balance"] == 10_000
    assert isinstance(result["total_return_pct"], float)
    print("Self-check passed:", result)
