from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Agent, Trade, DailySnapshot, TradeStatus
from backend.analytics.metrics import compute_correlation_matrix, compute_attribution
from backend.config import settings

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/portfolio")
async def get_portfolio_summary():
    """Portfolio-level summary: total P&L, rolling Sharpe, max drawdown, win rate."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        if not agents:
            return {
                "total_pnl": 0.0, "sharpe_ratio": None, "max_drawdown": None,
                "win_rate": 0.0, "return_30d_pct": 0.0, "agent_count": 0,
            }

        total_pnl = sum((a.total_pnl or 0.0) for a in agents)
        total_trades = sum((a.total_trades or 0) for a in agents)
        total_wins = sum((a.winning_trades or 0) for a in agents)
        win_rate = round((total_wins / total_trades * 100), 1) if total_trades else 0.0

        # Last 30 days: sum daily_return_pct across all agents
        cutoff = (date.today() - timedelta(days=30)).isoformat()
        snapshots = session.execute(
            select(DailySnapshot)
            .where(DailySnapshot.date >= cutoff)
            .order_by(DailySnapshot.date)
        ).scalars().all()

        # Aggregate by date
        by_date: dict[str, float] = {}
        for s in snapshots:
            by_date[s.date] = by_date.get(s.date, 0.0) + (s.daily_return_pct or 0.0)
        daily_returns = list(by_date.values())

        from backend.analytics.metrics import compute_sharpe, compute_max_drawdown
        sharpe = compute_sharpe(daily_returns) if len(daily_returns) >= 10 else None
        equity = [100.0 + sum(daily_returns[:i+1]) for i in range(len(daily_returns))]
        max_dd = compute_max_drawdown(equity) if len(equity) >= 2 else None
        return_30d = round(sum(daily_returns), 2) if daily_returns else 0.0

        return {
            "total_pnl": round(total_pnl, 2),
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "return_30d_pct": return_30d,
            "agent_count": len(agents),
        }


@router.get("/equity-curve")
async def get_equity_curve(
    days: int = Query(default=30, ge=1, le=365),
    agent_id: Optional[int] = Query(default=None),
):
    """Daily equity data for chart. agent_id=None means portfolio total."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        q = select(DailySnapshot).where(DailySnapshot.date >= cutoff).order_by(DailySnapshot.date)
        if agent_id is not None:
            q = q.where(DailySnapshot.agent_id == agent_id)
        snapshots = session.execute(q).scalars().all()

    if agent_id is not None:
        return [{"date": s.date, "pnl": s.total_pnl, "return_pct": s.daily_return_pct} for s in snapshots]

    # Aggregate portfolio by date
    by_date: dict[str, float] = {}
    for s in snapshots:
        by_date[s.date] = by_date.get(s.date, 0.0) + (s.total_pnl or 0.0)
    return [{"date": d, "pnl": round(p, 2)} for d, p in sorted(by_date.items())]


@router.get("/leaderboard")
async def get_leaderboard(sort_by: str = Query(default="return", enum=["return", "sharpe", "win_rate", "trades"])):
    """All agents sorted by chosen metric."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()

        # Pull latest snapshot per agent — single query instead of N+1
        all_snaps = session.execute(
            select(DailySnapshot)
            .order_by(DailySnapshot.agent_id, DailySnapshot.date.desc())
        ).scalars().all()

        latest: dict[int, DailySnapshot] = {}
        for snap in all_snaps:
            if snap.agent_id not in latest:
                latest[snap.agent_id] = snap

    rows = []
    for a in agents:
        snap = latest.get(a.id)
        rows.append({
            "id": a.id,
            "name": a.name,
            "room": a.room,
            "total_pnl": round((a.total_pnl or 0.0), 2),
            "return_pct": snap.daily_return_pct if snap else 0.0,
            "sharpe_ratio": snap.sharpe_ratio if snap else None,
            "max_drawdown": snap.max_drawdown if snap else None,
            "win_rate": round((a.win_rate or 0.0), 1),
            "total_trades": (a.total_trades or 0),
            "confidence_score": (a.confidence_score or 0),
            "status": a.status.value,
        })

    sort_key = {
        "return": lambda r: r["total_pnl"],
        "sharpe": lambda r: r["sharpe_ratio"] or -999,
        "win_rate": lambda r: r["win_rate"],
        "trades": lambda r: r["total_trades"],
    }[sort_by]
    rows.sort(key=sort_key, reverse=True)
    return rows


@router.get("/correlation")
async def get_correlation():
    """Pairwise Pearson correlation of last 30d daily returns per agent."""
    cutoff = (date.today() - timedelta(days=30)).isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        agent_names = {a.id: a.name for a in agents}

        snapshots = session.execute(
            select(DailySnapshot)
            .where(DailySnapshot.date >= cutoff)
            .order_by(DailySnapshot.date)
        ).scalars().all()

    # Build {agent_name: [daily_return_pct, ...]} in date order
    by_agent: dict[str, list[float]] = {}
    for s in snapshots:
        name = agent_names.get(s.agent_id, str(s.agent_id))
        by_agent.setdefault(name, []).append(s.daily_return_pct or 0.0)

    return compute_correlation_matrix(by_agent)


@router.get("/attribution")
async def get_attribution(date_str: Optional[str] = Query(default=None, alias="date")):
    """Per-agent P&L contribution for a given date (default: today)."""
    target_date = date_str or date.today().isoformat()

    with get_db_session(settings.DATABASE_URL) as session:
        date_start = datetime.fromisoformat(target_date)
        date_end = date_start + timedelta(days=1)

        trades = session.execute(
            select(Trade)
            .where(Trade.status == TradeStatus.CLOSED)
            .where(Trade.pnl.isnot(None))
            .where(Trade.closed_at >= date_start)
            .where(Trade.closed_at < date_end)
        ).scalars().all()

        agents = session.execute(select(Agent)).scalars().all()
        agent_names = {str(a.id): a.name for a in agents}

    trade_dicts = [
        {
            "agent_id": t.agent_id,
            "pnl": t.pnl,
            "closed_at": t.closed_at.isoformat() if t.closed_at else "",
        }
        for t in trades
    ]

    contributions = compute_attribution(trade_dicts, target_date)
    named = {agent_names.get(k, k): v for k, v in contributions.items()}

    return {
        "date": target_date,
        "contributions": named,   # {agent_name: pct_contribution}
    }
