from backend.config import settings
from backend.database.db import get_db_session
from backend.database.models import User
from backend.notifications.models import UserNotificationPreferences
from backend.notifications.service import NotificationService
from backend.utils.logger import logger

notification_service = NotificationService()  # module-level singleton


def notify_trade_executed(user_id: str, agent_name: str, symbol: str, action: str, pnl: float) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_trade:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Trade Executed: {action} {symbol}"
            body = f"Agent {agent_name} executed {action} on {symbol}. PnL: {pnl:.2f}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_trade_executed failed: {e}")


def notify_agent_paused(user_id: str, agent_name: str, reason: str) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_agent_pause:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Agent Paused: {agent_name}"
            body = f"Agent {agent_name} was paused. Reason: {reason}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_agent_paused failed: {e}")


def notify_drawdown_warning(user_id: str, agent_name: str, drawdown_pct: float) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.notify_on_drawdown:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = f"Drawdown Warning: {agent_name}"
            body = f"Agent {agent_name} drawdown at {drawdown_pct:.1%}"
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"notify_drawdown_warning failed: {e}")


def send_daily_digest(user_id: str, summary: dict) -> None:
    try:
        with get_db_session(settings.DATABASE_URL) as db:
            prefs = db.query(UserNotificationPreferences).filter_by(user_id=user_id).first()
            if not prefs or not prefs.daily_digest:
                return
            user = db.query(User).filter_by(id=user_id).first()
            if not user:
                return
            subject = "Daily Trading Digest"
            body = (
                f"Daily Summary\n"
                f"Total PnL: {summary.get('total_pnl', 0):.2f}\n"
                f"Trades: {summary.get('trade_count', 0)}\n"
                f"Best Agent: {summary.get('best_agent', 'N/A')}\n"
                f"Worst Agent: {summary.get('worst_agent', 'N/A')}"
            )
            if prefs.email_enabled:
                notification_service.send_email(user.email, subject, body)
            if prefs.sms_enabled and prefs.phone_number:
                notification_service.send_sms(prefs.phone_number, body)
    except Exception as e:
        logger.error(f"send_daily_digest failed: {e}")
