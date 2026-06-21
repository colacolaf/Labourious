from datetime import date, datetime, time
from backend.database.db import get_db_session
from backend.database.models import User, Agent, Trade, TradeStatus
from backend.notifications.triggers import send_daily_digest
from backend.utils.logger import logger


def run_daily_digest(database_url: str) -> None:
    today_dt = datetime.combine(date.today(), time.min)
    logger.info(f"Running daily digest for {today_dt.date().isoformat()}")
    try:
        with get_db_session(database_url) as db:
            from backend.notifications.models import UserNotificationPreferences
            prefs_list = db.query(UserNotificationPreferences).filter_by(daily_digest=True).all()
            for prefs in prefs_list:
                try:
                    user = db.query(User).filter_by(id=prefs.user_id).first()
                    if not user:
                        continue
                    agents = db.query(Agent).filter_by(user_id=prefs.user_id).all()
                    agent_ids = [a.id for a in agents]
                    trades = (
                        db.query(Trade)
                        .filter(
                            Trade.agent_id.in_(agent_ids),
                            Trade.status == TradeStatus.CLOSED,
                            Trade.closed_at >= today_dt,
                        )
                        .all()
                    ) if agent_ids else []
                    total_pnl = sum(t.pnl or 0 for t in trades)
                    agent_pnl = {}
                    for t in trades:
                        agent_pnl[t.agent_id] = agent_pnl.get(t.agent_id, 0) + (t.pnl or 0)
                    best_id = max(agent_pnl, key=agent_pnl.get) if agent_pnl else None
                    worst_id = min(agent_pnl, key=agent_pnl.get) if agent_pnl else None
                    agent_map = {a.id: a.name for a in agents}
                    summary = {
                        "total_pnl": total_pnl,
                        "trade_count": len(trades),
                        "best_agent": agent_map.get(best_id, "N/A"),
                        "worst_agent": agent_map.get(worst_id, "N/A"),
                    }
                    send_daily_digest(prefs.user_id, summary)
                except Exception as e:
                    logger.error(f"digest failed for user {prefs.user_id}: {e}")
    except Exception as e:
        logger.error(f"daily digest job failed: {e}")
