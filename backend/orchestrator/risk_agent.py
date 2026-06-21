"""Portfolio-level risk meta-agent. Monitors portfolio drawdown and pauses all agents on breach."""
import logging
from sqlalchemy.orm import Session
from backend.database.models import Agent, AgentStatus
from backend.api.websocket import manager

logger = logging.getLogger(__name__)


class RiskAgent:
    MAX_PORTFOLIO_DRAWDOWN = -0.25

    def __init__(self, db_session_factory):
        self.db_factory = db_session_factory

    async def run(self):
        """Monitor portfolio and pause all agents if drawdown exceeds threshold."""
        session = self.db_factory()
        try:
            agents = session.query(Agent).filter(Agent.is_active == True).all()
            stats = self._compute_stats(agents)

            if stats["portfolio_drawdown"] < self.MAX_PORTFOLIO_DRAWDOWN:
                await self._pause_all_agents(
                    agents, session,
                    f"Portfolio drawdown {stats['portfolio_drawdown']:.2%} < {self.MAX_PORTFOLIO_DRAWDOWN:.2%}",
                )
                return

            await manager.broadcast({
                "event": "portfolio_update",
                "total_pnl": stats["total_pnl"],
                "total_capital": stats["total_capital"],
                "portfolio_drawdown": stats["portfolio_drawdown"],
                "agent_count": stats["agent_count"],
                "paused_count": stats["paused_count"],
            })
        finally:
            session.close()

    def _compute_stats(self, agents: list) -> dict:
        total_pnl = sum(a.total_pnl or 0.0 for a in agents)
        total_capital = sum(a.paper_trading_balance or 0.0 for a in agents)
        portfolio_drawdown = (total_pnl / total_capital) if total_capital > 0 else 0.0
        paused_count = sum(1 for a in agents if a.status == AgentStatus.PAUSED)
        return {
            "total_pnl": total_pnl,
            "total_capital": total_capital,
            "portfolio_drawdown": portfolio_drawdown,
            "agent_count": len(agents),
            "paused_count": paused_count,
        }

    async def _pause_all_agents(self, agents: list, session: Session, reason: str):
        for agent in agents:
            agent.status = AgentStatus.PAUSED
        session.commit()

        try:
            if agents[0].user_id:
                from backend.notifications.triggers import notify_agent_paused
                for agent in agents:
                    notify_agent_paused(agent.user_id, agent.name, reason)
        except Exception:
            pass

        await manager.broadcast({
            "event": "bodyguard_pause_all",
            "reason": reason,
            "paused_count": len(agents),
        })
        logger.warning(f"Bodyguard: paused {len(agents)} agents — {reason}")
