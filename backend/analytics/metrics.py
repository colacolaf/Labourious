import math
from typing import Optional


def compute_sharpe(daily_returns: list[float], risk_free_rate: float = 0.0) -> float:
    if len(daily_returns) < 2:
        return 0.0
    n = len(daily_returns)
    mean = sum(daily_returns) / n
    variance = sum((r - mean) ** 2 for r in daily_returns) / (n - 1)
    std = math.sqrt(variance)
    if std == 0.0:
        return 0.0
    return round((mean - risk_free_rate) / std * math.sqrt(252), 4)


def compute_max_drawdown(equity_curve: list[float]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    peak = equity_curve[0]
    max_dd = 0.0
    for value in equity_curve[1:]:
        if value > peak:
            peak = value
        dd = (value - peak) / peak
        if dd < max_dd:
            max_dd = dd
    return round(max_dd, 6)


def compute_correlation_matrix(
    agents_daily_returns: dict[str, list[float]]
) -> dict[str, dict[str, float]]:
    agents = list(agents_daily_returns.keys())
    if len(agents) < 2:
        return {}

    def pearson(xs: list[float], ys: list[float]) -> float:
        n = min(len(xs), len(ys))
        if n < 2:
            return 0.0
        xs, ys = xs[:n], ys[:n]
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        dx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        dy = math.sqrt(sum((y - my) ** 2 for y in ys))
        if dx == 0 or dy == 0:
            return 0.0
        return round(num / (dx * dy), 4)

    result: dict[str, dict[str, float]] = {}
    for i, a in enumerate(agents):
        for j, b in enumerate(agents):
            if i >= j:
                continue
            corr = pearson(agents_daily_returns[a], agents_daily_returns[b])
            result.setdefault(a, {})[b] = corr
            result.setdefault(b, {})[a] = corr
    return result


def compute_attribution(
    trades: list[dict], date_str: str
) -> dict[str, float]:
    day_trades = [
        t for t in trades
        if t.get("closed_at", "")[:10] == date_str and t.get("pnl") is not None
    ]
    if not day_trades:
        return {}

    total_gross = sum(abs(t["pnl"]) for t in day_trades)
    if total_gross == 0.0:
        return {}

    result: dict[str, float] = {}
    for t in day_trades:
        key = str(t["agent_id"])
        pct = round((t["pnl"] / total_gross) * 100, 2)
        result[key] = result.get(key, 0.0) + pct
    return result
