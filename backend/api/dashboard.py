from fastapi import APIRouter, Query
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional

from backend.database.models import Agent, Trade, Performance, AgentStatus
from backend.database.db import get_db_session
from backend.config import settings

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
async def get_summary():
    """Portfolio summary: total P&L, agent counts, trade counts."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        trades = session.execute(select(Trade)).scalars().all()

        total_pnl = sum(a.total_pnl for a in agents)
        active_count = sum(1 for a in agents if a.is_active)
        running_count = sum(1 for a in agents if a.status == AgentStatus.RUNNING)
        closed_trades = [t for t in trades if t.pnl is not None]
        wins = sum(1 for t in closed_trades if (t.pnl or 0) > 0)
        win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0

        return {
            "total_pnl": round(total_pnl, 2),
            "agent_count": len(agents),
            "active_agents": active_count,
            "running_agents": running_count,
            "total_trades": len(trades),
            "closed_trades": len(closed_trades),
            "win_rate": round(win_rate, 1),
        }


@router.get("/performance")
async def get_performance_leaderboard():
    """Agent leaderboard sorted by total P&L."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent).order_by(Agent.total_pnl.desc())).scalars().all()
        return [
            {
                "id": a.id,
                "name": a.name,
                "symbol": a.symbol,
                "total_pnl": round(a.total_pnl, 2),
                "win_rate": round(a.win_rate, 1),
                "total_trades": a.total_trades,
                "status": a.status,
                "confidence_score": a.confidence_score,
            }
            for a in agents
        ]


@router.get("/allocation")
async def get_allocation():
    """Capital allocation per agent."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent).where(Agent.is_active == True)).scalars().all()
        total_balance = sum(a.paper_trading_balance for a in agents) or 1
        return [
            {
                "id": a.id,
                "name": a.name,
                "balance": a.paper_trading_balance,
                "allocation_pct": round(a.paper_trading_balance / total_balance * 100, 1),
            }
            for a in agents
        ]


@router.get("/equity-curve")
async def get_equity_curve(days: int = Query(30, le=365)):
    """Aggregated daily equity curve from Performance records."""
    since = datetime.utcnow() - timedelta(days=days)
    with get_db_session(settings.DATABASE_URL) as session:
        records = session.execute(
            select(Performance)
            .where(Performance.timestamp >= since)
            .order_by(Performance.timestamp.asc())
        ).scalars().all()

        # Aggregate by date
        daily: dict = {}
        for r in records:
            day = r.timestamp.date().isoformat()
            daily[day] = daily.get(day, 0.0) + r.total_pnl

        return [{"date": d, "pnl": round(v, 2)} for d, v in sorted(daily.items())]


@router.get("/risk")
async def get_risk_summary():
    """Risk overview: agents near pause threshold."""
    with get_db_session(settings.DATABASE_URL) as session:
        agents = session.execute(select(Agent)).scalars().all()
        at_risk = [
            {
                "id": a.id,
                "name": a.name,
                "confidence_score": a.confidence_score,
                "consecutive_losses": a.consecutive_losses,
                "current_drawdown": round(a.current_drawdown, 2),
            }
            for a in agents
            if a.confidence_score < 35 or a.consecutive_losses >= 2
        ]
        return {"agents_at_risk": at_risk, "total_at_risk": len(at_risk)}
