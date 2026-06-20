"""APScheduler EOD job — writes one DailySnapshot row per agent."""
from datetime import datetime, date
from sqlalchemy import select

from backend.database.db import get_db_session
from backend.database.models import Agent, Trade, DailySnapshot, TradeStatus
from backend.analytics.metrics import compute_sharpe, compute_max_drawdown
from backend.utils.logger import setup_logger

logger = setup_logger("snapshot_job")


def run_eod_snapshot(database_url: str) -> None:
    today = date.today().isoformat()
    logger.info(f"Running EOD snapshot for {today}")

    with get_db_session(database_url) as session:
        agents = session.execute(select(Agent)).scalars().all()

        for agent in agents:
            # Skip if row already exists for today (idempotent)
            existing = session.execute(
                select(DailySnapshot)
                .where(DailySnapshot.agent_id == agent.id)
                .where(DailySnapshot.date == today)
            ).scalar_one_or_none()
            if existing:
                continue

            # Closed trades for this agent (all time — for rolling metrics)
            trades = session.execute(
                select(Trade)
                .where(Trade.agent_id == agent.id)
                .where(Trade.status == TradeStatus.CLOSED)
                .where(Trade.pnl.isnot(None))
            ).scalars().all()

            trade_count = len(trades)
            wins = sum(1 for t in trades if (t.pnl or 0) > 0)
            win_rate = round((wins / trade_count * 100), 2) if trade_count else 0.0

            # Daily return pct relative to paper_trading_balance baseline
            baseline = agent.paper_trading_balance or 100_000.0
            daily_return_pct = round((agent.total_pnl / baseline) * 100, 4) if baseline else 0.0

            # Sharpe from last 30 snapshots (rolling)
            past_snapshots = session.execute(
                select(DailySnapshot)
                .where(DailySnapshot.agent_id == agent.id)
                .order_by(DailySnapshot.date.desc())
                .limit(29)
            ).scalars().all()

            rolling_returns = [s.daily_return_pct for s in past_snapshots] + [daily_return_pct]
            sharpe = compute_sharpe(rolling_returns) if len(rolling_returns) >= 10 else None

            # Equity curve from snapshots for drawdown
            equity = [baseline + (s.total_pnl or 0) for s in reversed(past_snapshots)]
            equity.append(baseline + agent.total_pnl)
            max_dd = compute_max_drawdown(equity) if len(equity) >= 2 else None

            snapshot = DailySnapshot(
                agent_id=agent.id,
                date=today,
                total_pnl=round(agent.total_pnl, 4),
                daily_return_pct=daily_return_pct,
                sharpe_ratio=sharpe,
                max_drawdown=max_dd,
                win_rate=win_rate,
                trade_count=trade_count,
            )
            session.add(snapshot)

        session.commit()
    logger.info(f"EOD snapshot complete for {today}")
